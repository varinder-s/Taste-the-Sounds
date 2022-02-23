# Taste-the-Sounds
## Overview
This is a web app designed to give food recommendations based off of a given song. The user can input any song that is on Spotify and the app will take the song and output a dish which complements that song. For example, if a user inputs  *Hello* by Adele, the output may be Broccoli with cheese soup. (Note that the results may change as the algorithm which selects the food adapts with each search)

There is also an option to register/log in which unlocks more features such as the ability to get different recommendations for a given song.

## project.db
This is the database where the song genres and user accounts are stored. To initially fill the database, hundreds of popular artists' discographies were parsed and the information of each song was aggregated based on the genres associated with the artist. The genres are used when finding the right food to go with a given song.

## app.py
This is the main application file which handles all of the web requests. Among others, this file has functions for the register, log in, and response pages.

### Register
The register page is a form which allows the user to create a username and a password. If the username is taken or the password and password confirmation do not match, the page will reload so the user can input a valid submission.

If the username and password is valid, the page redirects the user to the log in page.

### Log In
The log in page allows the user to log into a registered account. If the username does not exist or the password is incorrect. The page will reload so the user can try again. Passwords are hashed in order to provide security to the user, but it is always recommended that you do not use the same password for multiple accounts across various platforms.

### Response
The response page is where the user will see the food that goes with the song. If the user is logged in, there will be a button that allows them to see different food pairings with the song. If they are not logged in, the button will be grayed out. All users are also able to use a button which will search Google for recipes of the food.

## helpers.py
`helpers.py` contains the helper functions that are necessary for the application to run properly. This is where the Spotify and Spoonacular APIs are called. The main functions in this file are `getTrack`, `getFood`, and `updateDB`.

### getTrack
`getTrack` will query the Spotify API using the input from the user and will return the song information from Spotify.

### getFood
`getFood` will return the food that pairs with the given song. To do this, it first gets the song features. Song features include objective information such as duration and tempo, as well as Spotify generated categories such as danceability and speechiness. For this analysis, I used the categories of danceability, energy, and valence. These were chosen based on the idea that they would be most accurate in creating an answer for each song.

The song features are normalized with the average feature values of the genres associated with the song's artists. They are then combined to create one song score value. This song score (+/- 10%) is used as a multiplier with the average number of calories a person eats in one meal in order to get a general range in which the Spoonacular API can search for a food.

### updateDB
For each search, the database containing the genre information is changed. The values of each new search are added into the aggregate. This is still the case if a song was searched before, meaning each time a song is searched for, it is weighed more heavily in its respective genres. This allows for songs to influence the results in proportion to their popularity.