# TimeMapper
As an Insight data science fellow (Sept 2019 - Dec 2019), in a short span of 3 weeks, I worked on developing Time mapper.
This repo is for visualization app TimeMapper.club. 

## Motivation
How long it takes to move from point A to point B in a city depends on what time one is navigating the distance. 
A 10 min commute at 9:00 pm in L.A easily translates to a 45 min commute at 9:00 am.
If you are new to a city and looking for a place to stay, it makes sense to have a tool that can show you where 
to rent a place based on one's travel time budget.
Say, I have only 30 mins to drive in the morning and I work at point B, then where should I rent a place , i.e. where should point A be ?
And all this makes sense, because rent gradients across LA are pretty flat, unlike traffic gradients.

## Methodology 
Google's distance-time API was accessed to generate distance-time database in PostgresSQL. 
Apartment.com was scrapped to access available rentals in the city. Zipcodes were used to merge the datasets. 
For each address, approximations were made, and the address was automatically asigned to the nearest  zipcode(lattitude, longitude).
All this data was then used to generate the **contour maps** that were the output of the map.

## Tools - 
Python was used for development. Flask & AWS for deployment.

## Slides - 
(Project Demo)[timemapper_demo.pdf]

