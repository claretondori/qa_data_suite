"""API tests against JSONPlaceholder (https://jsonplaceholder.typicode.com), a free public fake REST API.

Note: it is a *fake* API. Writes (POST/PUT/DELETE) return realistic responses but are never saved.
Tests marked known_gap document where it differs from what a production API should do.
"""
import re
from urllib.parse import quote
import pytest
import requests

BASE = "https://jsonplaceholder.typicode.com"
TIMEOUT = 10
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

@pytest.fixture(scope="session")
def api():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session

def url(path):
    return f"{BASE}{path}"

# ---------- successful requests ----------
def test_get_single_post_has_expected_fields_and_types(api):
    r = api.get(url("/posts/1"), timeout=TIMEOUT)
    assert r.status_code == 200
    assert "application/json" in r.headers["Content-Type"]
    body = r.json()
    assert set(body) == {"userId", "id", "title", "body"}
    assert body["id"] == 1 and isinstance(body["userId"], int)
    assert isinstance(body["title"], str) and body["title"].strip() != ""

def test_list_posts_returns_100_posts_with_unique_ids(api):
    posts = api.get(url("/posts"), timeout=TIMEOUT).json()
    ids = [p["id"] for p in posts]
    assert len(posts) == 100
    assert len(set(ids)) == len(ids), "duplicate post ids in the listing"

def test_filter_by_user_returns_only_that_users_posts(api):
    posts = api.get(url("/posts"), params={"userId": 1}, timeout=TIMEOUT).json()
    assert len(posts) > 0
    assert {p["userId"] for p in posts} == {1}

def test_nested_comments_belong_to_the_post_and_have_valid_emails(api):
    comments = api.get(url("/posts/1/comments"), timeout=TIMEOUT).json()
    assert len(comments) > 0
    assert all(c["postId"] == 1 for c in comments)
    bad = [c["email"] for c in comments if not EMAIL_RE.match(c["email"])]
    assert not bad, f"malformed emails: {bad}"

def test_every_post_author_exists_in_users(api):
    """Referential integrity: no orphan posts."""
    author_ids = {p["userId"] for p in api.get(url("/posts"), timeout=TIMEOUT).json()}
    user_ids = {u["id"] for u in api.get(url("/users"), timeout=TIMEOUT).json()}
    assert author_ids <= user_ids

def test_todos_completed_flag_is_a_real_boolean(api):
    todos = api.get(url("/todos"), timeout=TIMEOUT).json()
    assert all(isinstance(t["completed"], bool) for t in todos)

# ---------- invalid input ----------
def test_nonexistent_post_returns_404_with_empty_body(api):
    r = api.get(url("/posts/999999"), timeout=TIMEOUT)
    assert r.status_code == 404
    assert r.json() == {}

@pytest.mark.parametrize("bad_id", ["abc", "-1", "0", "1.5", "1%20OR%201=1", quote("'; DROP TABLE posts;--")])
def test_malformed_post_id_is_rejected_with_404(api, bad_id):
    r = api.get(url(f"/posts/{bad_id}"), timeout=TIMEOUT)
    assert r.status_code == 404

def test_filter_with_non_matching_value_returns_empty_list_not_error(api):
    r = api.get(url("/posts"), params={"userId": "abc"}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() == []

def test_put_on_collection_is_not_allowed(api):
    r = api.put(url("/posts"), json={"title": "x"}, timeout=TIMEOUT)
    assert r.status_code in (404, 405)

# ---------- writes and edge cases ----------
def test_create_post_returns_201_and_echoes_payload(api):
    payload = {"title": "QA test", "body": "hello", "userId": 1}
    r = api.post(url("/posts"), json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    created = r.json()
    assert {k: created[k] for k in payload} == payload
    assert isinstance(created["id"], int)

def test_create_post_survives_unicode_and_a_very_long_body(api):
    payload = {"title": "Habari 🌍 café", "body": "é" * 10_000, "userId": 1}
    r = api.post(url("/posts"), json=payload, timeout=TIMEOUT)
    assert r.status_code == 201
    assert r.json()["body"] == payload["body"]

def test_update_post_with_put_returns_updated_fields(api):
    payload = {"id": 1, "title": "updated", "body": "new body", "userId": 1}
    r = api.put(url("/posts/1"), json=payload, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["title"] == "updated"

def test_delete_post_returns_200(api):
    assert api.delete(url("/posts/1"), timeout=TIMEOUT).status_code == 200

def test_created_post_is_not_actually_persisted(api):
    """Characterisation test: documents that this fake API does not save writes."""
    new_id = api.post(url("/posts"), json={"title": "t", "body": "b", "userId": 1}, timeout=TIMEOUT).json()["id"]
    assert api.get(url(f"/posts/{new_id}"), timeout=TIMEOUT).status_code == 404

def test_response_time_is_reasonable(api):
    r = api.get(url("/posts/1"), timeout=TIMEOUT)
    assert r.elapsed.total_seconds() < 5

# ---------- known gaps: what a production API SHOULD do ----------
@pytest.mark.known_gap
@pytest.mark.xfail(reason="API accepts an empty body and returns 201; a real API should return 400/422", strict=False)
def test_create_post_with_empty_body_should_be_rejected(api):
    r = api.post(url("/posts"), json={}, timeout=TIMEOUT)
    assert r.status_code in (400, 422)

@pytest.mark.known_gap
@pytest.mark.xfail(reason="API does not validate field types (userId as string accepted)", strict=False)
def test_create_post_with_wrong_type_should_be_rejected(api):
    r = api.post(url("/posts"), json={"title": 123, "body": None, "userId": "not-a-number"}, timeout=TIMEOUT)
    assert r.status_code in (400, 422)
