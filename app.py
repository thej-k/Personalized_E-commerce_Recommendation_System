import pickle
import streamlit as st
import pandas as pd
from PIL import Image
import requests
from io import BytesIO
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pymysql

# Set page config once at the very top
st.set_page_config(page_title="E-Commerce Recommendation System", layout="wide")

# Initialize session state for login status (default: False)
if 'login_status' not in st.session_state:
    st.session_state['login_status'] = False

# Connect to your MySQL database
def verify_login(user_name, password):
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='200281000790',
        database='rec_system'
    )

    cursor = connection.cursor()
    query = "SELECT user_id FROM users WHERE user_name = %s AND password = %s"
    cursor.execute(query, (user_name, password))

    result = cursor.fetchone()
    cursor.close()
    connection.close()

    if result:
        return result[0]  # Return the user_id
    return None




# Check login status using session state
if not st.session_state['login_status']:
    # Display login form if user is not logged in
    login_container = st.empty()
    
    with login_container.form(key='login_form'):
        st.header("Login to Access the System")
        user_name = st.text_input("Enter User Name:")
        password = st.text_input("Enter Password:", type='password')

        submit_button = st.form_submit_button("Login")

        if submit_button:
            user_id = verify_login(user_name, password)
            if user_id:
                st.session_state['login_status'] = True
                st.session_state['user_id'] = user_id
                st.success("Login successful! Redirecting to the main application...")
                # Empty the login container to hide the login form
                login_container.empty()  
            else:
                st.error("Invalid User Name or Password")
    
    # Stop the app if not logged in, so that it does not render further content
    #st.stop()

# Once the user is logged in, show the home page
if st.session_state['login_status']:
    st.write("Welcome to the E-Commerce Recommendation System!")


# Check login status using session state
if 'login_status' not in st.session_state or not st.session_state.login_status:
    st.warning("You need to login first!")
    # Redirect to login page using query parameters
    st.query_params['page'] = "login"
    st.stop()


# Load the data
items = pickle.load(open('item_list.pkl', 'rb'))
item_names = items['Name'].unique()

st.header("E-Commerce Recommendation System")

selected_item = st.selectbox('Select item from dropdown', item_names)

if st.button('Show Recommendations'):

    # Function for content-based recommendations
    def content_based_recommendations(items, item_name, top_n=5):
        # Check if the selected item exists in the dataset
        if item_name not in items['Name'].values:
            st.write(f"Item '{item_name}' not found in the data.")
            return pd.DataFrame()
        
        # Convert the 'Tags' column into a TF-IDF matrix for content-based filtering
        tfidf_vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix_content = tfidf_vectorizer.fit_transform(items['Tags'])
        
        # Compute cosine similarities between items based on their content (Tags)
        cosine_similarities_content = cosine_similarity(tfidf_matrix_content, tfidf_matrix_content)
        
        # Find the index of the selected item in the dataset
        item_index = items[items['Name'] == item_name].index[0]
        
        # Get a list of similarity scores for the selected item
        similar_items = list(enumerate(cosine_similarities_content[item_index]))
        
        # Sort the similar items in descending order of similarity (excluding the selected item itself)
        similar_items = sorted(similar_items, key=lambda x: x[1], reverse=True)
        top_similar_items = similar_items[1:top_n+1]  # Exclude the first item (itself)
        
        # Get the indices of the recommended items
        recommended_item_indices = [x[0] for x in top_similar_items]
        
        # Fetch the details of the recommended items
        recommended_items = items.iloc[recommended_item_indices][['Name', 'ReviewCount', 'Brand', 'ImageURL', 'Rating']]
        
        return recommended_items

    # Call the content-based recommendation function
    recommendations = content_based_recommendations(items, selected_item)

    # Display the recommended items in a 2-column layout
    # st.subheader("Recommended Items:")

    if not recommendations.empty:
        for idx, (index, row_data) in enumerate(recommendations.iterrows()):
            # Display items in two columns
            col1, col2 = st.columns([1, 2])  # Col1 for image, Col2 for text info
            
            with col1:
                # Fetch and resize the image to a fixed size
                try:
                    response = requests.get(row_data['ImageURL'])
                    img = Image.open(BytesIO(response.content))
                    img = img.resize((150, 150))  # Resize image to 150x150 pixels
                    st.image(img)
                except:
                    st.write("Image not available")
            
            with col2:
                # Display product name, brand, and rating
                st.write(f"**Name:** {row_data['Name']}")
                st.write(f"**Brand:** {row_data['Brand']}")
                st.write(f"**Rating:** {row_data['Rating']:.1f}")



def collaborative_filtering_recommendations(train_data, target_user_id, top_n = 10):
  #Create the user-item matrix
  user_item_matrix = train_data.pivot_table(index = 'ID', columns = 'ProdID', values = 'Rating', aggfunc = 'mean').fillna(0).astype(int)

  #Calculate the user similarity matrix
  user_similarity = cosine_similarity(user_item_matrix)

  #Find the index of the target user in the matrix
  target_user_index = user_item_matrix.index.get_loc(target_user_id)

  #Get the similarity scores for the target user
  user_similarities = user_similarity[target_user_index]

  #sort the users by similarity in descending order(excluding the target user)
  similar_user_indices = user_similarities.argsort()[::-1][1:]

  #Generate recommendations based on similar users
  recommend_items = []

  for user_index in similar_user_indices:
    #Get items rated by the similar user but not by the target user
    rated_by_similar_user = user_item_matrix.iloc[user_index]
    not_rated_by_target_user = (rated_by_similar_user == 0) & (user_item_matrix.iloc[target_user_index] ==0)

    #Extract the item IDs of recommended items
    recommend_items.extend(user_item_matrix.columns[not_rated_by_target_user][:10])

  #Get the details of recommended items
  recommended_items_details = train_data[train_data['ProdID'].isin(recommend_items)][['Name', 'ReviewCount', 'Brand', 'ImageURL', 'Rating' ]]

  return recommended_items_details.head()




# Get recommendations using the logged-in user ID
user_id = st.session_state.user_id
recommendations = collaborative_filtering_recommendations(items, user_id)

st.subheader("Items that matches your search")
for index, row in recommendations.iterrows():
    col1, col2 = st.columns([1, 2])  # Col1 for image, Col2 for text info
            
    with col1:
        try:
            response = requests.get(row['ImageURL'])
            img = Image.open(BytesIO(response.content))
            img = img.resize((150, 150))  # Resize image to 150x150 pixels
            st.image(img)
        except:
            st.write("Image not available")
            
    with col2:
        st.write(f"**Name:** {row['Name']}")
        st.write(f"**Brand:** {row['Brand']}")
        st.write(f"**Rating:** {row['Rating']:.1f}")






# Function for rating-based recommendation
def rating_based_recommendations(items, item_name, top_n=10):
    # Get the average ratings for each item
    average_ratings = items.groupby(['Name', 'ReviewCount', 'Brand', 'ImageURL'])['Rating'].mean().reset_index()
    
    # Sort the items based on ratings
    top_rated_items = average_ratings.sort_values(by='Rating', ascending=False)
    
    # Get the top_n rated items
    rating_based_recommendation = top_rated_items.head(top_n)
    
    return rating_based_recommendation

# Get recommendations
recommendations = rating_based_recommendations(items, selected_item)

# Display the recommended items in a 2-column layout
st.subheader("Top Rated Items:")

for idx, (index, row_data) in enumerate(recommendations.iterrows()):
    if idx >= 10:  # Ensure only 10 items are displayed
        break
    
    # Display items in two columns
    col1, col2 = st.columns([1, 2])  # Col1 for image, Col2 for text info
    
    with col1:
        # Fetch and resize the image to a fixed size
        try:
            response = requests.get(row_data['ImageURL'])
            img = Image.open(BytesIO(response.content))
            img = img.resize((150, 150))  # Resize image to 150x150 pixels
            st.image(img)
        except:
            st.write("Image not available")
    
    with col2:
        # Display product name, brand, and rating
        st.write(f"**Name:** {row_data['Name']}")
        st.write(f"**Brand:** {row_data['Brand']}")
        st.write(f"**Rating:** {row_data['Rating']:.1f}")
