from flask import Flask, render_template, request, jsonify
from flask import session, redirect, url_for
import random
from string import ascii_uppercase
from flask_cors import CORS
import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly
import plotly.figure_factory as ff
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import datetime

app = Flask(__name__)
CORS(app)

app.config["SECRET_KEY"] = "hjhjsdahhds"

api_key = '54f5fef66dd24f61a654f4f36667b65f'

#--------------------------------------Data preprocessing for Analysis -------------------------------------
players_s = pd.read_csv('athletes.csv')
regions = pd.read_csv('region.csv')
medals_df = pd.read_csv('medals.csv')

# Drop rows with empty 'athlete_full_name' and 'athlete_url'
medals_df = medals_df.dropna(subset=['athlete_full_name', 'athlete_url'])

# Step 3: Create a mapping of player names to player_ids
unique_names = medals_df["athlete_full_name"].unique().tolist()

# Step 4: Add the player_id column to the "Medals" dataset
player_id_map = {name: idx + 1 for idx, name in enumerate(unique_names)}
medals_df["player_id"] = medals_df["athlete_full_name"].map(player_id_map)

sports_url = medals_df['discipline_title'].dropna().unique().tolist()
sports_url.sort()

country_url = medals_df['country_name'].dropna().unique().tolist()
country_url.sort()

data = players_s.merge(regions, on='NOC', how='left')

Df = pd.concat([data, pd.get_dummies(data['Medal'])], axis=1)
medal_tally = Df.drop_duplicates(subset=['Team', 'NOC', 'Games', 'Year', 'City', 'Sport', 'Event', 'Medal'])
medal_tally = medal_tally.groupby('region').sum()[['Gold', 'Silver', 'Bronze']].sort_values('Gold', ascending=False).reset_index()
medal_tally['total'] = medal_tally['Gold'] + medal_tally['Silver'] + medal_tally['Bronze']

years = Df['Year'].unique().tolist()
years.sort()
years.insert(0, 'Overall')

country = np.unique(Df['region'].dropna().tolist()).tolist()
country.sort()
country.insert(0, 'Overall')

sports = np.unique(Df['Sport'].dropna().tolist()).tolist()
sports.sort()
sports.insert(0, 'Overall')

athlete = pd.read_csv('athlete_events.csv')
athlete = athlete[athlete['Season']=='Summer']
limited_players_s = players_s[players_s['Year'] <= 2016]
sorted_players_s = limited_players_s.sort_values(by='Name', ascending=True)
sorted_athlete = athlete.sort_values(by='Name',ascending = True)

sorted_players_s['Player_ID'] = range(1, len(limited_players_s) + 1)
sorted_athlete['Player_ID'] = range(1, len(sorted_athlete) + 1)

sorted_hw = sorted_players_s.merge(sorted_athlete[['Player_ID', 'Height', 'Weight']], on='Player_ID', how='left')
#------------------------------------Data preprocessing ends here---------------------------------

#----------------------------------- Home page -------------------------------------e
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# -------------------------------------- Quiz and Videos -------------------------------------
@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

@app.route('/highlights')
def highlights():
    return render_template('highlights.html')
        
#-------------------------------------Olympics Analysis app---------------------------------------- 

def fetch_medal(years, country):
    mf = Df.drop_duplicates(subset=['Team', 'NOC', 'Games', 'Year', 'City', 'Sport', 'Event', 'Medal'])

    if years == 'Overall' and country == 'Overall':
        temp_df = mf
    elif years == 'Overall' and country != 'Overall':
        temp_df = mf[mf['region'] == country]
    elif years != 'Overall' and country == 'Overall':
        temp_df = mf[mf['Year'] == int(years)]
    elif years != 'Overall' and country != 'Overall':
        temp_df = mf[(mf['Year'] == int(years)) & (mf['region'] == country)]

    x = temp_df.groupby('region').sum()[['Gold', 'Silver', 'Bronze']].sort_values('Gold', ascending=False).reset_index()
    x['total'] = x['Gold'] + x['Silver'] + x['Bronze']

    return x.to_dict('records')  # Convert DataFrame to a list of dictionaries

def most_success(Df,sports):
    
    temp_df = Df.dropna(subset=['Medal'])
    
    if sports!= 'Overall':
        temp_df = temp_df[temp_df['Sport']==sports]
        
    success = temp_df['Name'].value_counts().reset_index().head(10).merge(Df,left_on='index',right_on='Name',how='left')[['index','Name_x','Sport','region']].drop_duplicates('index')
    success.rename(columns={'index':'Name','Name_x':'Medals'},inplace=True)
    
    return success.to_dict('records')

def success(Df,country):
    
    temp_df = Df.dropna(subset=['Medal'])
    
    temp_df = temp_df[temp_df['region']==country]
        
    successfull = temp_df['Name'].value_counts().reset_index().head(10).merge(Df,left_on='index',right_on='Name',how='left')[['index','Name_x','Sport']].drop_duplicates('index')
    successfull.rename(columns={'index':'Name','Name_x':'Medals'},inplace=True)
    
    return successfull.to_dict('records')

@app.route('/medal', methods=['GET', 'POST'])  # Allow both GET and POST methods
def medal():
    if request.method == 'POST':
        selected_year = request.form.get('year')
        selected_country = request.form.get('country')
    else:
        # If the request is GET, use default values or 'Overall'
        selected_year = 'Overall'
        selected_country = 'Overall'

    medal_data = fetch_medal(selected_year, selected_country)

    return render_template('medals.html', years=years, country=country, medal_data=medal_data)


@app.route('/overall', methods=['GET', 'POST'])
def overall():
    Time = Df['Year'].nunique() - 1
    Places = Df['City'].nunique()
    Games = Df['Sport'].nunique()
    Events = Df['Event'].nunique()
    Athletes = Df['Name'].nunique()
    Countries = Df['region'].nunique()
    
    Nations = Df.drop_duplicates(subset=['Year', 'region'])['Year'].value_counts().reset_index().sort_values('index')
    Nations.rename(columns={'index': 'Edition', 'Year': 'No of countries'}, inplace=True)
    fign = px.line(Nations, x="Edition", y="No of countries")
    nations_graph = json.dumps(fign, cls=plotly.utils.PlotlyJSONEncoder)
    
    events = Df.drop_duplicates(subset=['Year', 'Event'])['Year'].value_counts().reset_index().sort_values('index')
    events.rename(columns={'index': 'Edition', 'Year': 'No of Events'}, inplace=True)
    fige = px.line(events, x="Edition", y="No of Events")
    events_graph = json.dumps(fige, cls=plotly.utils.PlotlyJSONEncoder)
    
    players = Df.drop_duplicates(subset=['Year', 'Name'])['Year'].value_counts().reset_index().sort_values('index')
    players.rename(columns={'index': 'Edition', 'Year': 'No of Athletes'}, inplace=True)
    figp = px.line(players, x="Edition", y="No of Athletes")
    players_graph = json.dumps(figp, cls=plotly.utils.PlotlyJSONEncoder)
    
    h = Df.drop_duplicates(['Year','Sport','Event'])
    x = h.pivot_table(index='Sport',columns='Year',values='Event',aggfunc='count').fillna(0).astype(int)
    
    # Create the heatmap using Plotly Express with the custom color scale
    figh = px.imshow(x, text_auto=True, width=1500, height=1800, color_continuous_scale='Viridis')
    
    heat_graph = json.dumps(figh, cls=plotly.utils.PlotlyJSONEncoder)
    
    game = request.form.get('sport')
    
    success_data = most_success(Df,game)
    
    return render_template('overall.html', Time=Time, Places=Places, Games=Games, Events=Events, Athletes=Athletes, Countries=Countries, nations_graph=nations_graph,events_graph=events_graph,players_graph=players_graph,heat_graph=heat_graph,success_data=success_data,sports=sports)
        

@app.route('/country',methods=['GET','POST'])
def country_wise_analysis():
    
    s_country = request.form.get('Countries')
    
    temp_df = Df.dropna(subset=['Medal'])
    temp_df = Df.drop_duplicates(subset=['Team', 'NOC', 'Games', 'Year', 'City', 'Sport', 'Event', 'Medal'])
    new_df = temp_df[temp_df['region'] == s_country]
    x = new_df.pivot_table(index='Sport',columns='Year',values='Medal',aggfunc='count').fillna(0).astype(int)
    final_df = new_df.groupby('Year', as_index=False)['Medal'].count()


    
    figc = px.line(final_df, x="Year", y="Medal")
    country_graph = json.dumps(figc, cls=plotly.utils.PlotlyJSONEncoder)
    
    
    figh = px.imshow(x, text_auto=True, width=1500, height=1400, color_continuous_scale='Viridis')
    figh.update_traces(textfont_size=5)
    heat_cgraph = json.dumps(figh, cls=plotly.utils.PlotlyJSONEncoder)
    
    successful_athletes = success(Df,s_country)
    
    return render_template('country.html',country_graph=country_graph,s_country=s_country,country=country,heat_cgraph=heat_cgraph,successful_athletes=successful_athletes)


@app.route('/athletes', methods=['GET', 'POST'])
def athletes():

    athlete_df = Df.drop_duplicates(subset=['Name', 'region'])
    
    x1 = athlete_df['Age'].dropna()
    x2 = athlete_df[athlete_df['Medal'] == 'Gold']['Age'].dropna()
    x3 = athlete_df[athlete_df['Medal'] == 'Silver']['Age'].dropna()
    x4 = athlete_df[athlete_df['Medal'] == 'Bronze']['Age'].dropna()
    
    figa = ff.create_distplot([x1, x2, x3, x4], ['Overall Age', 'Gold Medalists', 'Silver Medalists', 'Bronze Medalists'],show_hist=False,show_rug=False)
    figa.update_layout(
                   xaxis=dict(title='Age'),
                   yaxis=dict(title='Density'),
                   height=600,  # Adjust the height as per your preference
                   width=1200)  # Adjust the width as per your preference

    athlete_graph = json.dumps(figa, cls=plotly.utils.PlotlyJSONEncoder)
    
    selected_sport = request.form.get('sport')
    sorted_hw['Medal'].fillna('No Medal',inplace=True)
    temp_df = sorted_hw[sorted_hw['Sport'] == selected_sport]
    temp_df.sort_values(by='Year', inplace=True)
    

# Create two subplots, one for males and one for females
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Male Players", "Female Players"))

    # Filter data for male and female players
    male_data = temp_df[temp_df['Sex'] == 'M']
    female_data = temp_df[temp_df['Sex'] == 'F']

    # Define color map for each medal type
    medal_colors = {
        'Gold': 'gold',
        'Silver': 'silver',
        'Bronze': 'brown'
    }

    # Default color for 'No Medal'
    default_color = 'blue'

    # Plot for male players
    for medal in temp_df['Medal'].unique():
        male_medal_data = male_data[male_data['Medal'] == medal]
        color = medal_colors.get(medal, default_color)
        fig.add_trace(go.Scatter(x=male_medal_data['Weight'], y=male_medal_data['Height'], 
                                mode='markers', name=f'Male - {medal}', marker_symbol='circle', 
                                marker_size=8, marker_color=color), row=1, col=1)

    # Plot for female players
    for medal in temp_df['Medal'].unique():
        female_medal_data = female_data[female_data['Medal'] == medal]
        color = medal_colors.get(medal, default_color)
        fig.add_trace(go.Scatter(x=female_medal_data['Weight'], y=female_medal_data['Height'], 
                                mode='markers', name=f'Female - {medal}', marker_symbol='circle', 
                                marker_size=8, marker_color=color), row=1, col=2)

    # Update layout and axis labels
    fig.update_layout(
                    xaxis=dict(title="Weight"),
                    yaxis=dict(title="Height"))

    
    h_graph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
    return render_template('athletes.html', athlete_graph=athlete_graph,h_graph=h_graph,sports=sports)

#------------------------------------------- News app ------------------------------------------

# Function to fetch news using the API
def fetch_news(page, q):
    current_date = datetime.datetime.now()
    yesterday = current_date - datetime.timedelta(days=1)
    yesterday_date = yesterday.strftime('%Y-%m-%d')
    
   
    # yesterday_date = datetime.strptime('2023-07-29', '%Y-%m-%d')
    url = f'https://newsapi.org/v2/everything?q={q}&from={yesterday_date}&language=en&pageSize=20&page={page}&sortBy=popularity'
    headers = {'x-api-key': api_key}
    response = requests.get(url, headers=headers)
    news_data = response.json()
    articles = news_data.get('articles', [])
    cleaned_articles = [{'title': article['title'], 'description': article['description'], 'urlToImage': article['urlToImage'], 'url': article['url']} for article in articles]
    return cleaned_articles, news_data.get('totalResults', 0)


@app.route('/api/news', methods=['GET'])
def get_news():
    current_query = "Olympics"
    current_page = 1

    # Fetch news for the current query and page
    articles, total_results = fetch_news(current_page, current_query)

    # If no articles found, return a message
    if total_results == 0:
        return jsonify({'message': 'No news articles found for the query "Olympics" on the specified date.'})

    first_five_articles = articles[:5]
    return jsonify(first_five_articles)
    
@app.route('/news')
def news():
    return render_template('news.html')

# ----------------------------------------- Players Profile app --------------------------------------

@app.route('/profile', methods=['GET','POST'])
def search_players():

    Country = request.form.get('country_name')
    Sport = request.form.get('discipline_title')
    filtered_players = medals_df[(medals_df['country_name'] == Country) & (medals_df['discipline_title'] == Sport)]
    filtered_players = filtered_players.sort_values(by='athlete_full_name', ascending=True)
    filtered_players = filtered_players.drop_duplicates(subset=['athlete_full_name', 'athlete_url'])[['athlete_full_name', 'athlete_url']]

    return render_template('players.html', players=filtered_players,country_url=country_url,sports_url=sports_url)

@app.route('/player/<int:player_id>')
def player_profile(player_id):
    player = medals_df.loc[medals_df['player_id'] == player_id].iloc[0]
    if not player.empty:
        return render_template('players.html', player=player)
    else:
        return 'Player not found', 404
    
if __name__ == "__main__":
    app.run()
