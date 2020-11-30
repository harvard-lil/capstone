title: Historical Trends
explainer: CAP Historical Trends visualizes and compares the frequency of terms in citable US caselaw between 1800 and 2018. It provides a simple, flexible search syntax and intuitive controls suitable for casual exploration, serious research, and everything between. The data is sourced directly from our free, public <a href="{% url 'api' %}">API</a>.

{# ==============> GETTING STARTED <============== #}
# Getting started {: data-toc-label='Start Here' }

The Caselaw Access Project includes over 6 million U.S. legal cases from the Harvard Law School 
Library — about 12 billion words in all. Our Historical Trends tool graphs the frequency of words and phrases through
time from 1800 to 2018, similar to the [Google Ngram Viewer](https://books.google.com/ngrams). (Though the corpus includes
data from cases before 1800, low case density limits their utility in visualizing trends, so we've excluded them.)

Search for phrases of one to three words. Multiple phrases can be separated by commas. Do not use quotes. 
All searches are case-insensitive. Examples:

* [`piracy`]({% url 'trends' %}?q=piracy) *(history of the term "piracy")*
* [`his or her`]({% url 'trends' %}?q=his or her) *(history of the term "his or her")*
* [`apple, banana, orange, pear`]({% url 'trends' %}?q=apple, banana, orange, pear) *(compare "apple" to "banana" to 
"orange" to "pear")*
* [`he said, she said`]({% url 'trends' %}?q=he said, she said) *(compare "he said" to "she said")*


{# ==============> READING THE RESULTS <============== #}
# Reading the results {: data-toc-label='Reading Results' }

## Key

The color/shape-keyed terms at the top of the graph correspond to each term in the query, and each of those corresponds 
to a trend line on the graph. The individual points on the trend line can be revealed by hovering over them with the 
pointer, or by using [keyboard navigation](#keyboard-navigation).

## Horizontal axis

The horizontal axis always represents time; each point on the timeline represents one or more years, depending on the 
[Smoothing](#setting-smoothing) setting. If no smoothing is applied, each point on the horizontal axis represents one 
year. If maximum smoothing is applied, it may be an average of several decades.  Hover over or focus on a data point to 
see what years each point represents. 

## Vertical axis

The numerically-labeled vertical axis is a little trickier. Depending on your [settings](#customize-display), it could 
represent: 

* the number of times that term was used in a given year
* out of all terms used that year, what percent were that term
* the number of cases in which that term was used in a given year
* the percentage of cases in which that term was used in a given year
* a different thing for each trend line if "Terms scaled to fill Y axis" option is selected. 

Read on for how to change those display settings.

{# ==============> CUSTOMIZE GRAPH DISPLAY <============== #}
# Customize display {: data-toc-label='Customize' }

## Percentage Count/Instance Count/Scaling

For example, in the query [{% url 'trends' %}?q=apple, banana, orange, pear]({% url 'trends' %}?q=apple,%20banana,%20orange,%20pear) 
we can see four terms: apple, banana, orange, and pear. For the sake of simplicity, we'll turn smoothing off by clicking 
on the gear icon and sliding
the smoothing slider all the way to the left, until 'No smoothing will be applied' is displayed.

If we focus on 1990, we see that 'pear' appears in 0.0065% of cases, 'banana' appears in 0.058% of cases, 'apple' 
appears in 0.45% of cases, and 'orange' appears in 1% of cases. This can be changed by tweaking the Percentage 
Count/Instance Count/Scaling settings, which are also accessible by clicking on the gear icon above the graph. By 
default, the settings read: 

* 'percentage' rather than 'absolute number,' 
* 'case count' rather than 'instance count,'
* 'Terms on the same Y axis' rather than 'Terms scaled to fill Y axis'

If we wanted to get the total number of cases containing those terms rather than the percentage of cases, select 
'Absolute number.' In this case, we see that 'pear' appears in 5 cases, 'banana' appears in 45 cases, 'apple' appears 
in 352, and 'orange' appears in 797 cases. If we want to change the unit to the number of times the term was used 
rather than the number of cases in which that term was used, select 'Instance count.' Doing so shows us that in 1990, 
even though 'apple' only appeared in 352 cases, the term was used 787 times. If we weren't interested at all in direct 
scalar comparison, the 'Terms scaled to fill Y axis' option changes the vertical scale of each trend line to fill the 
vertical space on the graph. You can still get the exact numbers of each data point by hovering over of focusing on a 
data point, but the placement of the data points are only relative to the other points on that trend line for that 
specific term, and not to the other terms. As a result, the Y-axis scale disappears.

## Smoothing

In the previous example, we turned smoothing off so one data point would equal one year. If we drag the smoothing
slider to the right until "Data points will be averaged with the nearest 10% of other points" is displayed, rather than 
each point on the horizontal access representing a single value for one year, it now represents a value averaged over 
42 years, and the previously bumpy trend line is now smooth. 

**Please keep in mind that smoothing does not simply flatten the curve; it changes the values of each data point.** 
The year labels, however, will not change. This means that with smoothing enabled, a data point associated with a 
particular year will have values from other years averaged into it. Smoothing affects data in both the graph and table 
views, but not CSV or JSON downloads.


{# ==============> TABLE VIEW <============== #}
# Table view

If you'd preview to view the data points in a table rather than on a chart, you can click on the table icon (between the
keyboard icon and the mortarboard icon) above the graph. These are affected by the 
[customize display settings](#customize-display) in the same way the graph is. 

**important: smoothing does not simply flatten the curve; it changes the values of the each data point. Please see the
[Smoothing](#setting-smoothing) section for more information.**


{# ==============> KEYBOARD NAVIGATION <============== #}
# Keyboard navigation

The graph is keyboard accessible. With the graph selected, press:

Keyboard Navigation Commands:

* **up and down arrows**: select terms
* **left and right arrows**: select points
* **space bar**: enable or disable selected trend line
* **enter key**: search for example cases

Keyboard Sound Commands:

* **"s"** key: audio tones on/off
* **"p"** key: auto play audio tones
* **"b"** key: blues mode


{# ==============> Download <============== #}
# Download

The data can be exported in four ways. The first three are accessible by clicking the download icon above the graph.

* Download as an image
    * best for sharing on social media, or messaging services
* Download CSV
    * best for analyzing in Excel or other human-centric data analysis tools
* Download JSON 
    * best for analyzing in a program you'd write
    
The final method, writing a program to use [our API]({% url 'api' %}) directly, provides the most flexibility and 
access to our data.

{# ==============> Wildcard search <============== #}
# Wildcard search

Replace the final word of a phrase with "*" to perform a wildcard search. This will return the top ten phrases beginning
with your first one or two words. Wildcards are currently allowed only as the final word in a phrase. 
 
Examples:

* [`constitutional *`]({% url 'trends' %}?q=constitutional *) *(top ten two-word phrases beginning with "constitutional")*
* [`ride a *`]({% url 'trends' %}?q=ride a *) *(top ten three-word phrases beginning with "ride a")*
* `* amendment` **(not currently supported)**{: class="highlighted" }


{# ==============> Jurisdiction Search <============== #}
# Jurisdiction search

Limit a term to a particular jurisdiction (US state or state-level political division) by starting the term with that 
jurisdiction's code. Available jurisdiction codes are listed below. 

Examples:

* [`cal: gold mine`]({% url 'trends' %}?q=cal: gold mine) *(history of the term "gold mine" in California)*
* [`me: lobster, cal: gold, tex: cowboy`]({% url 'trends' %}?q=me: lobster, cal: gold, tex: cowboy) *(compare "lobster" 
in Maine, "gold" in California, and "cowboy" in Texas)*

Show all jurisdictions separately by using the special jurisdiction code "*". 

Examples:

* [`*: gold`]({% url 'trends' %}?q=*: gold) *(compare "gold" in all jurisdictions separately)*


{# ==============> JURISDICTION CODES <============== #}
# Jurisdiction codes

* Wildcard: " *:"
* Alabama: " ala:"
* Alaska: " alaska:"
* American Samoa: " am-samoa:"
* Arizona: " ariz:"
* Arkansas: " ark:"
* California: " cal:"
* Colorado: " colo:"
* Connecticut: " conn:"
* Dakota Territory: " dakota-territory:"
* District of Columbia: " dc:"
* Delaware: " del:"
* Florida: " fla:"
* Georgia: " ga:"
* Guam: " guam:"
* Hawaii: " haw:"
* Idaho: " idaho:"
* Illinois: " ill:"
* Indiana: " ind:"
* Iowa: " iowa:"
* Kansas: " kan:"
* Kentucky: " ky:"
* Louisiana: " la:"
* Massachusetts: " mass:"
* Maryland: " md:"
* Maine: " me:"
* Michigan: " mich:"
* Minnesota: " minn:"
* Mississippi: " miss:"
* Missouri: " mo:"
* Montana: " mont:"
* Native American: " native-american:"
* Navajo Nation: " navajo-nation:"
* North Carolina: " nc:"
* North Dakota: " nd:"
* Nebraska: " neb:"
* Nevada: " nev:"
* New Hampshire: " nh:"
* New Jersey: " nj:"
* New Mexico: " nm:"
* Northern Mariana Islands: " n-mar-i:"
* New York: " ny:"
* Ohio: " ohio:"
* Oklahoma: " okla:"
* Oregon: " or:"
* Pennsylvania: " pa:"
* Puerto Rico: " pr:"
* Rhode Island: " ri:"
* South Carolina: " sc:"
* South Dakota: " sd:"
* Tennessee: " tenn:"
* Texas: " tex:"
* Tribal Jurisdictions: " tribal:"
* United States: " us:"
* Utah: " utah:"
* Virginia: " va:"
* Virgin Islands: " vi:"
* Vermont: " vt:"
* Washington: " wash:"
* Wisconsin: " wis:"
* West Virginia: " w-va:"
* Wyoming: " wyo:" 


{# ==============> CITATION FEATURE <============== #}
# Citation feature

The citation feature automatically generates citations in APA, MLA, Chicago / Turabian, and Bluebook formats. Click on
the mortarboard (graduation cap) icon above the graph to access the citations.


