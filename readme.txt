functions:
1. user_details() 
if request method is GET
    gets user_id and checks if the role is Employee or Manager, if 'Employee' displays employee detail and manager_name else if 'Manager' displays the employees reporting to the manager.
if request method is PATCH
    user can change the username,email and password alone

2. add_user()
    only admin can add new employees
3. change_manager()
    only admin can change the manager assigned
4. change_role()
    only admin can change role
5. assign_task()
    only manager can assign task to the employees   