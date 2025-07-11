import requests

def get_all_users():
    response = requests.get("http://localhost:8000/api/users/all") # Assuming your backend runs on localhost:8000
    response.raise_for_status()  # Raises an exception for bad status codes
    users_data = response.json()
    
    # Transform the data to the desired format
    transformed_users = []
    for user in users_data:
        transformed_users.append({
            "username": user.get("username"),
            "interests_description": user.get("interests_description", [])
        })
    return transformed_users

def get_user_interest(username: str):
    # user_email is the email of the user
    response = requests.get(f"http://localhost:8000/api/users/by_email/{username}") 
    response.raise_for_status() # Raises an exception for bad status codes (e.pyg., 404)
    user_data = response.json()
    return user_data.get("interests_description", [])

# print(get_all_users())
print(get_user_interest("111@tongji.edu.cn"))
print(get_all_users())
