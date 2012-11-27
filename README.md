========
Basic Description
========

The program takes a query string on the command line, like so
  
    alex@lambda:~/spotify$ python -m spotify "if i can't let it go out of my mind."
  
and prints out a list of matched song names and their urls.


As far as the rules of engagement are concerned:

1. It uses redis to cache lookups between runs of the program. (So, running redis on localhost is required to run the script.)
2. It uses the threading module to issue searches against the API (in a single thread application we would wait a long time for the results).
3. It is case insensitive with regard to the capitalization of the query.

Now, when a line is given to the program (let's say the line is "it's sunny today"), what the script does is split this line into multiple queries
like so:

1. it's
2. it's sunny
3. it's sunny outside
4. sunny
5. sunny outside
6. outside

And then tries to find a matching song title for each of the above-generated strings. It stops looking after requesting a maximum of 2 pages.
The reason why I do this is because I try to get as close to the optimal solution as possible, which requires trying out all of the subcomponents of the query.

Once the script discovers whether each of 1-6 has a matching song title, it then tries to return to the user as few song titles as possible.




