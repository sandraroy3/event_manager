import pytest
import logging
from httpx import AsyncClient
from app.main import app
from app.services.jwt_service import decode_token
from app.utils.nickname_gen import generate_nickname
from urllib.parse import urlencode

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Fixture for common user data
@pytest.fixture
def user_data():
    return {
        "nickname": generate_nickname(),
        "email": "test@example.com",
        "password": "sS#fdasrongPassword123!",
    }

# Fixture for authorization headers
@pytest.fixture
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}

# Helper function to check status codes and response content
async def assert_status_code(response, expected_code, expected_detail=None):
    assert response.status_code == expected_code
    if expected_detail:
        assert expected_detail in response.json().get("detail", "")

# Test 1: Create User Access Denied
async def test_create_user_access_denied(async_client, user_token, user_data, auth_headers):
    logger.info("Testing user creation with access denied.")
    
    response = await async_client.post("/users/", json=user_data, headers=auth_headers)
    
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response content: {response.text}")
    
    assert response.status_code == 403, f"Expected 403 but got {response.status_code}"

# Test 2: Retrieve User Access Denied
@pytest.mark.asyncio
async def test_retrieve_user_access_denied(async_client, verified_user, user_token, auth_headers):
    response = await async_client.get(f"/users/{verified_user.id}", headers=auth_headers)
    await assert_status_code(response, 403)

# Test 3: Retrieve User Access Allowed
@pytest.mark.asyncio
async def test_retrieve_user_access_allowed(async_client, admin_user, admin_token, auth_headers):
    response = await async_client.get(f"/users/{admin_user.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(admin_user.id)

# Test 4: Update User Email Access Denied
@pytest.mark.asyncio
async def test_update_user_email_access_denied(async_client, verified_user, user_token, auth_headers):
    updated_data = {"email": f"updated_{verified_user.id}@example.com"}
    response = await async_client.put(f"/users/{verified_user.id}", json=updated_data, headers=auth_headers)
    await assert_status_code(response, 403)

# Test 5: Update User Email Access Allowed
@pytest.mark.asyncio
async def test_update_user_email_access_allowed(async_client, admin_user, admin_token, auth_headers):
    updated_data = {"email": f"updated_{admin_user.id}@example.com"}
    response = await async_client.put(f"/users/{admin_user.id}", json=updated_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == updated_data["email"]

# Test 6: Delete User
@pytest.mark.asyncio
async def test_delete_user(async_client, admin_user, admin_token, auth_headers):
    delete_response = await async_client.delete(f"/users/{admin_user.id}", headers=auth_headers)
    assert delete_response.status_code == 204
    fetch_response = await async_client.get(f"/users/{admin_user.id}", headers=auth_headers)
    assert fetch_response.status_code == 404

# Test 7: Create User Duplicate Email
@pytest.mark.asyncio
async def test_create_user_duplicate_email(async_client, verified_user):
    user_data = {
        "email": verified_user.email,
        "password": "AnotherPassword123!",
    }
    response = await async_client.post("/register/", json=user_data)
    await assert_status_code(response, 400, "Email already exists")

# Test 8: Create User Invalid Email
@pytest.mark.asyncio
async def test_create_user_invalid_email(async_client):
    user_data = {
        "email": "notanemail",
        "password": "ValidPassword123!",
    }
    response = await async_client.post("/register/", json=user_data)
    await assert_status_code(response, 422)

# Test 9: Login Success
@pytest.mark.asyncio
async def test_login_success(async_client, verified_user):
    form_data = {
        "username": verified_user.email,
        "password": "MySuperPassword$1234"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    decoded_token = decode_token(data["access_token"])
    assert decoded_token is not None, "Failed to decode token"
    assert decoded_token["role"] == "AUTHENTICATED"

# Test 10: Login User Not Found
@pytest.mark.asyncio
async def test_login_user_not_found(async_client):
    form_data = {
        "username": "nonexistentuser@here.edu",
        "password": "DoesNotMatter123!"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    await assert_status_code(response, 401, "Incorrect email or password.")

# Test 11: Login Incorrect Password
@pytest.mark.asyncio
async def test_login_incorrect_password(async_client, verified_user):
    form_data = {
        "username": verified_user.email,
        "password": "IncorrectPassword123!"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    await assert_status_code(response, 401, "Incorrect email or password.")

# Test 12: Login Unverified User
@pytest.mark.asyncio
async def test_login_unverified_user(async_client, unverified_user):
    form_data = {
        "username": unverified_user.email,
        "password": "MySuperPassword$1234"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 401

# Test 13: Delete User Does Not Exist
@pytest.mark.asyncio
async def test_delete_user_does_not_exist(async_client, admin_token):
    non_existent_user_id = "00000000-0000-0000-0000-000000000000"
    headers = {"Authorization": f"Bearer {admin_token}"}
    delete_response = await async_client.delete(f"/users/{non_existent_user_id}", headers=headers)
    await assert_status_code(delete_response, 404)

# Test 14: Update User Github Profile
@pytest.mark.asyncio
async def test_update_user_github(async_client, admin_user, admin_token, auth_headers):
    updated_data = {"github_profile_url": "http://www.github.com/kaw393939"}
    response = await async_client.put(f"/users/{admin_user.id}", json=updated_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["github_profile_url"] == updated_data["github_profile_url"]

# Test 15: Update User LinkedIn Profile
@pytest.mark.asyncio
async def test_update_user_linkedin(async_client, admin_user, admin_token, auth_headers):
    updated_data = {"linkedin_profile_url": "http://www.linkedin.com/kaw393939"}
    response = await async_client.put(f"/users/{admin_user.id}", json=updated_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["linkedin_profile_url"] == updated_data["linkedin_profile_url"]

# Test 16: List Users as Admin
@pytest.mark.asyncio
async def test_list_users_as_admin(async_client, admin_token):
    response = await async_client.get(
        "/users/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

# Test 17: List Users as Manager
@pytest.mark.asyncio
async def test_list_users_as_manager(async_client, manager_token):
    response = await async_client.get(
        "/users/",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 200

# Test 18: List Users Unauthorized
@pytest.mark.asyncio
async def test_list_users_unauthorized(async_client, user_token):
    response = await async_client.get(
        "/users/",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    await assert_status_code(response, 403)
