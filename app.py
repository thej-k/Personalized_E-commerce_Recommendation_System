import pickle
import streamlit as st
import pandas as pd
from PIL import Image
import requests
from io import BytesIO
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pymysql
import streamlit.components.v1 as components


st.set_page_config(page_title="E-Commerce Recommendation System", layout="wide")

# Initialize session state for login status (default: False)
if 'login_status' not in st.session_state:
    st.session_state['login_status'] = False

video_url = "https://raw.githubusercontent.com/thej-k/Personalized_E-commerce_Recommendation_System/main/e_commerce.mp4"

# Connect to MySQL database
def verify_login(user_name, password):
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='200300600860',
        database='rec_system'
    )

    cursor = connection.cursor()
    query = "SELECT user_id FROM users WHERE user_name = %s AND password = %s"
    cursor.execute(query, (user_name, password))

    result = cursor.fetchone()
    cursor.close()
    connection.close()

    if result:
        return result[0] 
    return None


# Check login status using session state
if not st.session_state['login_status']:
    login_container = st.empty()
    
    with login_container.form(key='login_form'):
        st.markdown('<div class="login-form-container">', unsafe_allow_html=True)
        st.header("Login to Access the System")
        user_name = st.text_input("Enter User Name:")
        password = st.text_input("Enter Password:", type='password')

        submit_button = st.form_submit_button("Login")
        st.markdown('</div>', unsafe_allow_html=True) 

        if submit_button:
            user_id = verify_login(user_name, password)
            if user_id:
                st.session_state['login_status'] = True
                st.session_state['user_id'] = user_id
                st.success("Login successful! Redirecting to the main application...")
                login_container.empty()  
            else:
                st.error("Invalid User Name or Password")
    

# Once the user is logged in, show the home page
if st.session_state['login_status']:
        # Video banner (autoplay, muted, loop)
    video_html = f"""
        <style>
        .video-container {{
            width: 100%;
            height: auto;
        }}
        .video-container video {{
            width: 100%;
            height: auto;
              margin-top: -200px;

        }}
        </style>
        <div class="video-container">
            <video autoplay muted loop>
                <source src="{video_url}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
    """

    # Render the video banner at the top
    components.html(video_html, height=400)  # Adjust the height as needed
    st.write("Welcome to the E-Commerce Recommendation System!")

st.markdown('<div class="page">', unsafe_allow_html=True)   
# Check login status using session state
if 'login_status' not in st.session_state or not st.session_state.login_status:
    st.warning("You need to login first!")
    # Redirect to login page using query parameters
    st.query_params['page'] = "login"
    st.stop()

# Get logged-in user ID
user_id = st.session_state.user_id

# Load the data
items = pickle.load(open('item_list.pkl', 'rb'))
item_names = items['Name'].unique()

st.header("E-Commerce Recommendation System")
num_columns = 5
selected_item = st.selectbox('Select item from dropdown', item_names)

# Function for content-based recommendations
def content_based_recommendations(items, item_name, top_n=10):
    if item_name not in items['Name'].values:
        st.write(f"Item '{item_name}' not found in the data.")
        return pd.DataFrame()
        
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix_content = tfidf_vectorizer.fit_transform(items['Tags'])
        
    cosine_similarities_content = cosine_similarity(tfidf_matrix_content, tfidf_matrix_content)
        
    item_index = items[items['Name'] == item_name].index[0]
        
    similar_items = list(enumerate(cosine_similarities_content[item_index]))
        
    similar_items = sorted(similar_items, key=lambda x: x[1], reverse=True)
    top_similar_items = similar_items[1:top_n+1]  
        
    recommended_item_indices = [x[0] for x in top_similar_items]
        
    recommended_items = items.iloc[recommended_item_indices][['Name', 'ReviewCount', 'Brand', 'ImageURL', 'Rating']]
        
    return recommended_items

def truncate_name(name, max_length=90):
    return (name[:max_length] + '...') if len(name) > max_length else name

# Function for collaborative filtering recommendations
def collaborative_filtering_recommendations(train_data, target_user_id, top_n = 10):
  user_item_matrix = train_data.pivot_table(index = 'ID', columns = 'ProdID', values = 'Rating', aggfunc = 'mean').fillna(0).astype(int)

  user_similarity = cosine_similarity(user_item_matrix)

  target_user_index = user_item_matrix.index.get_loc(target_user_id)

  user_similarities = user_similarity[target_user_index]

  similar_user_indices = user_similarities.argsort()[::-1][1:]

  recommend_items = []

  for user_index in similar_user_indices:
    rated_by_similar_user = user_item_matrix.iloc[user_index]
    not_rated_by_target_user = (rated_by_similar_user == 0) & (user_item_matrix.iloc[target_user_index] ==0)

    recommend_items.extend(user_item_matrix.columns[not_rated_by_target_user][:10])

  recommended_items_details = train_data[train_data['ProdID'].isin(recommend_items)][['Name', 'ReviewCount', 'Brand', 'ImageURL', 'Rating' ]]

  return recommended_items_details.head()


if st.button('Show Recommendations'):
    #Function for hybrid recommendations
    def hybrid_recommendation_systems(train_data, target_user_id, item_name, top_n=10):
        content_based_rec = content_based_recommendations(train_data, item_name, top_n)
        collaborative_filtering_rec = collaborative_filtering_recommendations(train_data, target_user_id, top_n)
        hybrid_recommendations = pd.concat([content_based_rec, collaborative_filtering_rec]).drop_duplicates()

        return hybrid_recommendations.head()
    

    recommendations = hybrid_recommendation_systems(items, user_id, selected_item)

   

    rowsR = [recommendations.iloc[i:i + num_columns] for i in range(0, len(recommendations), num_columns)]

    for row in rowsR:
        cols = st.columns(num_columns)

        for idx,col in enumerate(cols):
            if idx < len(row):

                row_data = row.iloc[idx]
                img_url = row_data['ImageURL']
                name = row_data['Name']
                truncated_name = truncate_name(name) 
                brand = row_data['Brand']
                rating = row_data['Rating']

                with col:
                    try:
                        # Download and resize the image to 150x200 pixels
                        response = requests.get(img_url)
                        img = Image.open(BytesIO(response.content))
                        img = img.resize((150, 150))  # Resize the image to a fixed size
                    except Exception as e:
                        st.write("Image not available")
                    
                    st.markdown(f"""
                        <div class="card">
                            <img src="{img_url}"  alt="Product Image">
                            <h4>{truncated_name}</h4>
                            <p><strong>Brand:</strong> {brand}</p>
                            <p><strong>Rating:</strong> {rating:.1f} ⭐</p>
                            <button>Add to cart</button>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                # Empty column if there are no more items in the row
                col.empty()
#calling collaborative filtering function
recommendations = collaborative_filtering_recommendations(items, user_id)

st.subheader("Items that matches your search :")

rowsM = [recommendations.iloc[i:i + num_columns] for i in range(0, len(recommendations), num_columns)]

for row in rowsM:
    cols = st.columns(num_columns)

    for idx,col in enumerate(cols):
        if idx < len(row):

            row_data = row.iloc[idx]
            img_url = row_data['ImageURL']
            name = row_data['Name']
            truncated_name = truncate_name(name) 
            brand = row_data['Brand']
            rating = row_data['Rating']

            with col:
                try:
                     # Download and resize the image to 150x200 pixels
                    response = requests.get(img_url)
                    img = Image.open(BytesIO(response.content))
                    img = img.resize((150, 150))  # Resize the image to a fixed size
                except Exception as e:
                    st.write("Image not available")
                
                st.markdown(f"""
                    <div class="card">
                        <img src="{img_url}"  alt="Product Image">
                        <h4>{truncated_name}</h4>
                        <p><strong>Brand:</strong> {brand}</p>
                        <p><strong>Rating:</strong> {rating:.1f} ⭐</p>
                        <button>Add to cart</button>
                    </div>
                """, unsafe_allow_html=True)
        else:
            # Empty column if there are no more items in the row
            col.empty()

# for index, row in recommendations.iterrows():
#     # Fetch the image URL
#     img_url = row['ImageURL']
#     name = row['Name']
#     brand = row['Brand']
#     rating = row['Rating']
    
#     # HTML structure for each card
#     card_html = f"""
#         <div class='cs'>
#         <div class="card">
#             <img src="{img_url}" alt="Product Image">
#             <h4>{name}</h4>
#             <p><strong>Brand:</strong> {brand}</p>
#             <p><strong>Rating:</strong> {rating:.1f} ⭐</p>
#         </div>
#         </div>
#     """
    
#     # Render the card using st.markdown
#     st.markdown(card_html, unsafe_allow_html=True)

# Function for rating-based recommendation
def rating_based_recommendations(items, top_n=10):
    average_ratings = items.groupby(['Name', 'ReviewCount', 'Brand', 'ImageURL'])['Rating'].mean().reset_index()
    
    top_rated_items = average_ratings.sort_values(by='Rating', ascending=False)
    
    rating_based_recommendation = top_rated_items.head(top_n)
    
    return rating_based_recommendation

# Get recommendations
recommendations = rating_based_recommendations(items)

st.subheader("Top Rated Items:")

# Custom styles for the card layout
st.markdown("""
    <style>
        .card {
            margin: 2px;  /* Adjust spacing between cards */
            width: 300px;  /* Set a maximum width for each card */
            height:450px;
            border: 1px solid #ddd;
            border-radius: 10px;
            box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
            padding: 20px;
            padding-bottom:2px;
            margin-bottom:25px;
            display: flex; /* Use flexbox */
            flex-direction: column; /* Align children vertically */
            justify-content: space-between;
        }
        .card img{
            width: 70%;
            height: 200px;
            border-bottom: 1px solid #ddd;
            margin-left:15%;
            }
        .card h4 {
            margin: 10px 0;
            font-size: 16px;
        }
        .card p {
            margin: 5px 0;
            font-size: 14px;
        }
        .card button {
            background-color: #ff5733; /* Vibrant orange color */
            color: white;  /* White text */
            border: none;  /* Remove default borders */
            padding: 10px 20px;  /* Add padding to make it bigger */
            border-radius: 25px;  /* Rounded corners */
            font-size: 16px;  /* Adjust the text size */
            cursor: pointer;  /* Change the cursor to a pointer */
            margin-bottom: 10px;
            transition: background-color 0.3s ease, transform 0.3s ease;  /* Smooth hover effect */
            
        }
        /* Hover effect for the button */
        .card button:hover {
            background-color: #c70039;  /* Change to darker red on hover */
            transform: translateY(-3px);  /* Slightly lift the button on hover */
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.2);  /* Add shadow on hover */
        }
        .login-form-container {
            max-width: 300px;  /* Adjust the max width of the form */
            margin: 0 auto;  /* Center the form horizontally */
            padding: 40px 20px;  /* Add padding around the form */
            background-color: #f9f9f9;  /* Optional: Add a background color */
            border-radius: 10px;  /* Optional: Round the corners */
            box-shadow: 2px 2px 12px rgba(0, 0, 0, 0.1);  /* Optional: Add a subtle shadow */
        }
        .page{
            width:100%;
            }
    </style>
""", unsafe_allow_html=True)



# Break recommendations into rows of `num_columns` cards
rows = [recommendations.iloc[i:i + num_columns] for i in range(0, len(recommendations), num_columns)]

for row in rows:
    # Create the columns for the current row
    cols = st.columns(num_columns)
    
    for idx, col in enumerate(cols):
        if idx < len(row):
            # Access the current card data
            row_data = row.iloc[idx]
            img_url = row_data['ImageURL']
            name = row_data['Name']
            truncated_name = truncate_name(name) 
            brand = row_data['Brand']
            rating = row_data['Rating']
            
            # Use the column to display the card
            with col:
                try:
                    # Download and resize the image to 150x200 pixels
                    response = requests.get(img_url)
                    img = Image.open(BytesIO(response.content))
                    img = img.resize((150, 150))  # Resize the image to a fixed size
                except Exception as e:
                    st.write("Image not available")

                # Apply the custom card style using HTML inside the column
                st.markdown(f"""
                    <div class="card">
                        <img src="{img_url}"  alt="Product Image">
                        <h4>{truncated_name}</h4>
                        <p><strong>Brand:</strong> {brand}</p>
                        <p><strong>Rating:</strong> {rating:.1f} ⭐</p>
                        <button>Add to cart</button>
                    </div>
                """, unsafe_allow_html=True)
        else:
            # Empty column if there are no more items in the row
            col.empty()

st.markdown('</div>', unsafe_allow_html=True)

 # if not recommendations.empty:
    #     for idx, (index, row_data) in enumerate(recommendations.iterrows()):
    #         # Display items in two columns
    #         col1, col2 = st.columns([1, 2])  # Col1 for image, Col2 for text info
            
    #         with col1:
    #             # Fetch and resize the image to a fixed size
    #             try:
    #                 response = requests.get(row_data['ImageURL'])
    #                 img = Image.open(BytesIO(response.content))
    #                 img = img.resize((150, 150))  # Resize image to 150x150 pixels
    #                 st.image(img)
    #             except:
    #                 st.write("Image not available")
            
    #         with col2:
    #             # Display product name, brand, and rating
    #             st.write(f"**Name:** {row_data['Name']}")
    #             st.write(f"**Brand:** {row_data['Brand']}")
    #             st.write(f"**Rating:** {row_data['Rating']:.1f}")