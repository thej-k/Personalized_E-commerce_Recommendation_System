# import streamlit as st
# import pymysql

# # Connect to your MySQL database
# def verify_login(user_name, password):
#     connection = pymysql.connect(
#         host='localhost',
#         user='root',
#         password='',
#         database='rec_system'
#     )
    
#     cursor = connection.cursor()
#     query = "SELECT user_id FROM users WHERE user_name = %s AND password = %s"
#     cursor.execute(query, (user_name, password))
    
#     result = cursor.fetchone()
#     cursor.close()
#     connection.close()
    
#     if result:
#         return result[0]  # Return the user_id
#     return None

# # Page configuration
# st.set_page_config(page_title="Login")

# # Login form
# st.title("Login to E-Commerce Recommendation System")

# user_name = st.text_input("Enter User Name:")
# password = st.text_input("Enter Password:", type='password')

# if st.button("Login"):
#     user_id = verify_login(user_name, password)
#     if user_id:
#         st.session_state['login_status'] = True
#         st.session_state['user_id'] = user_id
#         st.success("Login successful! Redirecting to the main application...")

#         # Redirect to the main application using query parameters
#         st.query_params['page'] = "home"
#         # Redirect to the main application using JavaScript
#         # st.markdown(f'<a href="app.py">Click here to redirect</a>')
        
#     else:
#         st.error("Invalid User Name or Password")
