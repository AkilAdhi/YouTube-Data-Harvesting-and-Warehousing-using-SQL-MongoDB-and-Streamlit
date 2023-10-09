#!/usr/bin/env python
# coding: utf-8

# In[1]:


from googleapiclient.discovery import build
import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu
from pymongo import MongoClient
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from datetime import datetime
import plotly.express as px
from PIL import Image


# In[6]:


api_key = ' '  - # enter your api here
youtube = build('youtube', 'v3', developerKey=api_key)


# In[214]:





# In[215]:


# Function to get channel data
def get_channel_data(youtube, channel_id):
    channel_data = youtube.channels().list(
        part='snippet,contentDetails,statistics',
        id=channel_id
    )
    response = channel_data.execute()
    data = dict(
        channel_name=response['items'][0]["snippet"]["title"],
        channel_id=response['items'][0]['id'],
        subscribers=response['items'][0]["statistics"]["subscriberCount"],
        views=response['items'][0]["statistics"]["viewCount"],
        total_videos=response['items'][0]["statistics"]["videoCount"],
        playlist_id=response['items'][0]["contentDetails"]["relatedPlaylists"]["uploads"],
        channel_description=response['items'][0]['snippet']['description']
    )

    return data



# In[216]:


data = get_channel_data(youtube, channel_id)


# In[220]:


# Function to get video IDs from playlist
def get_video_ids(youtube, playlist_id):
    request = youtube.playlistItems().list(
        part='contentDetails',
        playlistId=playlist_id,
        maxResults=50
    )
    response = request.execute()

    video_ids = []

    for item in response['items']:
        video_ids.append(item['contentDetails']['videoId'])

    next_page_token = response.get('nextPageToken')

    while next_page_token:
        request = youtube.playlistItems().list(
            part='contentDetails',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response['items']:
            video_ids.append(item['contentDetails']['videoId'])

        next_page_token = response.get('nextPageToken')

    return video_ids


# In[221]:


video_ids = get_video_ids(youtube, playlist_id)


# In[223]:


def convert_duration(duration_string):
    # By calling timedelta() without any arguments, the duration
    # object is initialized with a duration of 0 days, 0 seconds, and 0 microseconds. Essentially, it sets the initial duration to zero.
    duration_string = duration_string[2:]  # Remove "PT" prefix
    duration = timedelta()
    
    # Extract hours, minutes, and seconds from the duration string
    if 'H' in duration_string:
        hours, duration_string = duration_string.split('H')
        duration += timedelta(hours=int(hours))
    
    if 'M' in duration_string:
        minutes, duration_string = duration_string.split('M')
        duration += timedelta(minutes=int(minutes))
    
    if 'S' in duration_string:
        seconds, duration_string = duration_string.split('S')
        duration += timedelta(seconds=int(seconds))
    
    # Format duration as H:MM:SS
    duration_formatted = str(duration)
    if '.' in duration_formatted:
        hours, rest = duration_formatted.split(':')
        minutes, seconds = rest.split('.')
        duration_formatted = f'{int(hours)}:{int(minutes):02d}:{int(seconds):02d}'
    else:
        duration_formatted = duration_formatted.rjust(8, '0')
    
    return duration_formatted




# In[224]:


def convert_timestamp(timestamp):
    datetime_obj = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    formatted_time = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


# In[225]:


# Function to get video details
def get_video_details(youtube, video_ids):
    all_video_stats = []

    for i in range(0, len(video_ids), 50):
        request = youtube.videos().list(
            part='snippet,statistics',
            id=','.join(video_ids[i:i+50])
        )
        
        req = youtube.videos().list(
            part='contentDetails',
            id=','.join(video_ids[i:i+50])
        )
        response = request.execute()
        res = req.execute()

        for video, vid in zip(response['items'], res['items']):
            video_stats = {
                'title': video['snippet']['title'],
                'video_id': video['id'],
                'channel_id': video['snippet']['channelId'],
                'published_date':convert_timestamp(video['snippet']['publishedAt']),
                'video_description': video['snippet']['description'],
                'views': video['statistics']['viewCount'],
                'likes': video['statistics']['likeCount'],
                'comments': video['statistics']['commentCount'],
                'time_duration': convert_duration(vid['contentDetails']['duration'])
            }
            
            all_video_stats.append(video_stats)
            
    return all_video_stats


# In[226]:


all_video_stats =  get_video_details(youtube, video_ids)


# In[228]:


def get_comment_details(youtube, video_ids):
    all_video_stats = []

    for video_id in video_ids:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=video_id
        )
        response = request.execute()

        # Process the response and append the comment details to all_video_stats
        for comments in response['items']:
            comment = dict(
                comment_id=comments["id"],
                comment_text=comments["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
                comment_author=comments["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
                comment_published_at=convert_timestamp(comments["snippet"]["topLevelComment"]["snippet"]["publishedAt"]),
                video_id= video_id[0]
            )
            all_video_stats.append(comment)

    return all_video_stats


# In[229]:


all_video_stats = get_comment_details(youtube, video_ids)


# In[232]:


def get_all_data(youtube, channel_id,video_ids):
                # Get the channel data
            channel_data = get_channel_data(youtube, channel_id)
            st.subheader('Channel Data')
            st.write(channel_data)

           # Get the video details
            video_details = get_video_details(youtube, video_ids)
            st.subheader('Video Details')
            st.write(video_details)

            # Comment data
            comment_details = get_comment_details(youtube, video_ids)
            st.subheader('Comments')
            st.write(comment_details)

            data_file = {'ch_id': channel_data,
                         'video_info': video_details,
                         'comments': comment_details}

            return data_file


# In[233]:


data_file = get_all_data(youtube, channel_id,video_ids)


# In[258]:


#function to store in mongodb
client = MongoClient('mongodb://localhost:27017/')
db = client['youtubedata']
collection = db['channel_info']
collection.insert_one(data_file)


# In[ ]:





# In[259]:


# Connect to MySQL
def create_tables():
    
    import mysql.connector
    import pymysql  
# Connect to MySQL
    mysql_connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='')
        #autocommit=True)

    mysql_cursor = mysql_connection.cursor()

    mysql_cursor.execute("CREATE DATABASE IF NOT EXISTS youtubedata")
    mysql_cursor.execute("USE youtubedata")
    
    create_channel_table = '''
        CREATE TABLE IF NOT EXISTS channel_data (
        channel_name VARCHAR(100),
        channel_id VARCHAR(500) PRIMARY KEY,
        subscribers INT,
        views_count INT,
        total_videos INT,
        playlist_id VARCHAR(100),
        channel_description TEXT
    );
'''
    mysql_cursor.execute(create_channel_table)
    mysql_cursor.fetchall()  # Consume the result

    create_video_table = '''
        CREATE TABLE IF NOT EXISTS video_details (
        title VARCHAR(500),
        video_id VARCHAR(255) PRIMARY KEY,
        channel_id VARCHAR(500),
        published_date DATE,
        video_description TEXT, 
        views BIGINT,
        likes BIGINT,
        comments BIGINT,
        time_duration VARCHAR(200)
    );
'''
    mysql_cursor.execute(create_video_table)
    mysql_cursor.fetchall()  # Consume the result

    create_comment_table = '''
        CREATE TABLE IF NOT EXISTS comment_details (
        comment_id INT PRIMARY KEY,
        comment_text TEXT,
        comment_author TEXT,
        comment_published_at DATE,
        video_id VARCHAR(255)
        
        );
'''
    mysql_cursor.execute(create_comment_table)
    mysql_cursor.fetchall()  # Consume the result

    mysql_connection.commit()
# Close the cursor and the connection
    mysql_cursor.close()
    mysql_connection.close()
    
    return True  



# In[260]:


create_tables()


# In[ ]:





# In[269]:


def store_in_sql():
    # Connect to MySQL
    mysql_connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='youtubedata',
        connect_timeout=1000 
    )
    
    mysql_cursor = mysql_connection.cursor()

    client = MongoClient('mongodb://localhost:27017/')
    db = client['youtubedata']
    collection = db['channel_info']
    
    mycollection = db['channel_info']
    
    document_names = []
    
    for i in mycollection.find():
        document_names.append(i)
    
    mongodata = pd.DataFrame(document_names)
    channel_file = mongodata['ch_id']
    video_file = mongodata['video_info']
    comments = mongodata['comments']
    
    
    channel_dat = []
    
    for i in range(len(channel_file)):
        channel_dataframe = channel_file[i]
        channel_dat.append(channel_dataframe)
    channel_dataframe = pd.DataFrame(channel_dat)
    
    channel_id_playlist_id = channel_dataframe[['channel_id', 'playlist_id']]
    
    video_dat = []
    for i in range(len(video_file)):
        all_videos = video_file[i]
        video_dat.extend(all_videos)
    video_info = pd.DataFrame(video_dat)
    
    comment_dat = []
    for i in range(len(comments)):
        all_comments = comments[i]
        comment_dat.extend(all_comments)
    comment_data = pd.DataFrame(comment_dat)
    
    #Inserting channel details
    insert_channeldetails = '''INSERT IGNORE INTO channel_data (channel_name, channel_id, subscribers, views_count, total_videos, playlist_id,channel_description) VALUES (%s, %s, %s, %s, %s, %s, %s)'''
    values = channel_dataframe.values.tolist()
    mysql_cursor.executemany(insert_channeldetails, values)
    
    # Inserting video details
    insert_videodetails = '''INSERT IGNORE INTO video_details (title, video_id, channel_id, published_date, video_description, views, likes, comments, time_duration)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)'''
    values = video_info.values.tolist()
    mysql_cursor.executemany(insert_videodetails, values)

    # Inserting comment details
    insert_commentdetails = '''INSERT IGNORE INTO comment_details (comment_id, comment_text, comment_author, comment_published_at, video_id) VALUES (%s, %s, %s, %s, %s)'''
    values = comment_data.values.tolist()
    mysql_cursor.executemany(insert_commentdetails, values)


    
    mysql_connection.commit()
    
    # Close the cursor and the connection
    mysql_cursor.close()
    mysql_connection.close()
    


# In[270]:


store_in_sql()


# In[ ]:





# In[271]:


def main():
    # SETTING STREAMLIT PAGE 

    with st.sidebar:
        choice = option_menu(None, ["Home","Loading Data to MongoDB","SQL Data Warehouse","Channel queries and Data Visualization"], 
                           icons=["house-door-fill"],
                           default_index=1,
                           orientation="vertical",
                           styles={"nav-link": {"font-size": "25px", "text-align": "centre", "margin": "0px", 
                                                "--hover-color": "#C80101"},
                                   "icon": {"font-size": "25px"},
                                   "container" : {"max-width": "8000px"},
                                   "nav-link-selected": {"background-color": "#C80101"}})
    
    if choice == "Home":
        # Title Image
        st.image("download.png")
        st.write("# :blue[Welcome to the YouTube Data Harvesting and Warehousing Project]")
       
    
    if choice == "Loading Data to MongoDB":
            st.write("## :red[Data Collection and Load Channel Data to MongoDB]")
            st.markdown("#    ")
            st.write("## Enter the YouTube Channel ID")
            ch_id = st.text_input("Get Channel ID from channel Page").split(',')
            if st.button("### :green[Data Collection]"):
                    st.write('### Data Collected Successfully')
            if st.button("### :green[Upload to MongoDB]"):
                with st.spinner('Please Wait for it...'):
                    st.write('### The Uploaded details:')
                    c=get_channel_data(youtube,ch_id)
                    #st.dataframe(c)
                    playlist_id=c['playlist_id']
                    v=get_video_ids(youtube,playlist_id)
                    vd= get_video_details(youtube, v)
                    cd=get_comment_details(youtube,v)
                    all_data_info=get_all_data(youtube, ch_id,v)
                    st.write(all_data_info)
                    store_in_mongodb(all_data_info)
                    st.write("## :red[Data Collection Successfully Stored to MongoDB]") 
              
    


    
    if choice=="SQL Data Warehouse":
        
        st.write("## :red[Data Migration from MongoDB to SQL]")
        st.markdown("#    ")
        import_to_sql=st.button("### :green[Migration_to_SQL]")
        st.write("Click the button to migrate data")
        if import_to_sql:
            create_tables()
            store_in_sql()
            st.write('### Migrated succcesfully')
            # st.experimental_rerun()
            

    if choice=="Channel queries and Data Visualization":
        
        st.write("## :red[Select any question to get Insights]")
        st.markdown("#    ")
        ques1 = '1.	What are the names of all the videos and their corresponding channels?'
        ques2 = '2.	Which channels have the most number of videos, and how many videos do they have?'
        ques3 = '3.	What are the top 10 most viewed videos and their respective channels?'
        ques4 = '4.	How many comments were made on each video, and what are their corresponding video names?'
        ques5 = '5.	Which videos have the highest number of likes, and what are their corresponding channel names?'
        ques6 = '6.	What is the total number of likes for each video, and what are their corresponding video names?'
        ques7 = '7.	What is the total number of views for each channel, and what are their corresponding channel names?'
        ques8 = '8.	What are the names of all the channels that have published videos in the year 2022?'
        ques9 = '9.	What is the average duration of all videos in each channel, and what are their corresponding channel names?'
        ques10 = '10.Which videos have the highest number of comments, and what are their corresponding channel names?'
        question = st.selectbox('Select your Queries',(ques1,ques2,ques3,ques4,ques5,ques6,ques7,ques8,ques9,ques10))
        clicked4 = st.button("### :green[SQL]")
        
        if clicked4:
            mysql_connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='youtubedata')
            
            mysql_cursor = mysql_connection.cursor()
           
            mysql_cursor.execute("SHOW DATABASES")
            databases = mysql_cursor.fetchall() 
            mysql_cursor.execute("USE youtubedata")
            
            if question == ques1:
                query = "select title AS Video_Title,channel_name AS Channel_Name FROM video_details AS A INNER JOIN channel_data AS B ON A.channel_id=B.channel_id;"
                mysql_cursor.execute(query)
                df = pd.DataFrame(mysql_cursor.fetchall(),columns=mysql_cursor.column_names)
                st.write(df)
            elif question == ques2:
                query = "select channel_name AS Channel_Name,total_videos AS Total_Videos from channel_data where total_videos=(SELECT MAX(total_videos) FROM channel_data);"
                mysql_cursor.execute(query)
                df = pd.DataFrame(mysql_cursor.fetchall(),columns=mysql_cursor.column_names)
                st.write(df)
                
            elif question == ques3:
                query = "select channel_name AS Channel_Name,title AS Video_Title,views AS Views from video_details as a inner join channel_data as b on a.channel_id=b.channel_id order by views desc limit 10;"
                mysql_cursor.execute(query)
                df = pd.DataFrame(mysql_cursor.fetchall(),columns=mysql_cursor.column_names)
                st.write(df)
                st.write("### :green[Top 10 most viewed videos :]")
                fig = px.bar(df,
                     x=mysql_cursor.column_names[2],
                     y=mysql_cursor.column_names[1],
                     orientation='h',
                     color=mysql_cursor.column_names[0]
                    )
                st.plotly_chart(fig,use_container_width=True)
            elif question == ques4:
                query = "select title AS Video_Title,comments AS Comments from video_details order by comments desc;"
                mysql_cursor.execute(query)
                df = pd.DataFrame(mysql_cursor.fetchall(),columns=mysql_cursor.column_names)
                st.write(df)
            elif question == ques5:
                query = "select channel_name AS Channel_name,title AS Title,likes AS Likes_Count from video_details as a inner join channel_data as b on a.channel_id=b.channel_id ORDER BY likes DESC LIMIT 10;"
                mysql_cursor.execute(query)
                df = pd.DataFrame(mysql_cursor.fetchall(),columns=mysql_cursor.column_names)
                st.write(df)
                
                st.write("### :green[Top 10 most liked videos :]")
                fig = px.bar(df,
                     x=mysql_cursor.column_names[2],
                     y=mysql_cursor.column_names[1],
                     orientation='h',
                     color=mysql_cursor.column_names[0]
                    )
                st.plotly_chart(fig,use_container_width=True)
                
            elif question == ques6:
                query = "select title AS Title,likes AS Likes_Count from video_details order by likes asc;"
                mysql_cursor.execute(query)
                df = pd.DataFrame(mysql_cursor.fetchall(),columns=mysql_cursor.column_names)
                st.write(df)
            elif question == ques7:
                query = "select channel_name AS Channel_Name,sum(views) AS total_video_count from video_details as a inner join channel_data as b on a.channel_id=b.channel_id group by b.channel_name order by sum(views);"
                mysql_cursor.execute(query)
                df = pd.DataFrame(mysql_cursor.fetchall(),columns=mysql_cursor.column_names)
                st.write(df)
                st.write("### :green[Channels vs Views :]")
                fig = px.bar(df,
                     x=mysql_cursor.column_names[0],
                     y=mysql_cursor.column_names[1],
                     orientation='v',
                     color=mysql_cursor.column_names[0]
                    )
                st.plotly_chart(fig,use_container_width=True)
            elif question == ques8:
                query = "select channel_name AS Channel_name,published_date AS Published_date from video_details as a inner join channel_data as b on a.channel_id=b.channel_id WHERE published_date BETWEEN '2022-01-01' AND '2022-12-31';"
                mysql_cursor.execute(query)
                df = pd.DataFrame(mysql_cursor.fetchall(),columns=mysql_cursor.column_names)
                st.write(df)
            elif question == ques9:
                query = "select channel_name AS Channel_name,avg(time_duration) AS Average_Video_Duration_hrs from video_details as a inner join channel_data as b on a.channel_id=b.channel_id group by b.channel_name;"
                mysql_cursor.execute(query)
                df = pd.DataFrame(mysql_cursor.fetchall(),columns=mysql_cursor.column_names)
                st.write(df)
                st.write("### :green[Avg video duration for channels :]")
                fig = px.bar(df,
                     x=mysql_cursor.column_names[0],
                     y=mysql_cursor.column_names[1],
                     orientation='v',
                     color=mysql_cursor.column_names[0]
                    )
                st.plotly_chart(fig,use_container_width=True)
            elif question == ques10:
                query = "select channel_name AS Channel_name,title AS Title,comments AS Comments from video_details as a inner join channel_data as b on a.channel_id=b.channel_id ORDER BY comments DESC LIMIT 10;;"
                mysql_cursor.execute(query)
                df = pd.DataFrame(mysql_cursor.fetchall(),columns=mysql_cursor.column_names)
                st.write(df)
            
    
            
            
if __name__ == '__main__':
    main()
    


# In[272]:





# In[ ]:




