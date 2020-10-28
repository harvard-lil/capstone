{% load pipeline %}
{% load api_url %}
title: Access Limits 
page_image: img/og_image/docs.png
meta_description: Access Limitations

The agreement with our project partner, [Ravel](http://ravellaw.com), requires us to limit access to the full
text of cases to no more than 500 cases per person, per day.

# Exceptions  {: class="subtitle" }
This limitation does not apply to 
[researchers]({% url 'docs' 'user_guides/documentation_glossary' %}#def-researchers) who agree to certain 
restrictions on use and redistribution. Nor does this restriction apply to cases issued in whitelisted jurisdictions.

# Whitelisted Jurisditions {: class="subtitle" }
Whitelisted jurisditions make their newly issued cases freely available online in an authoritative, citable, 
machine-readable format. 

Currently, these are the only whitelisted jurisdictions:
 
* Illinois
* Arkansas
* New Mexico
* North Carolina 
{: add_list_class="spacious-list pl-4" }
 
We would love to whitelist more jurisdictions! If you are involved in US case publishing at the state or federal level,
we'd love to talk to you about making the transition to digital-first publishing. Please 
[contact us]({% url "contact" %}) and introduce yourself! Also, check out our 
[information for courts]({% url "docs" "user_pathways/for-courts/index" %}).
  
# Research Access {: class="subtitle" }
Some users may qualify for unlimited access as a research scholar. For more information, visit our 
[research access guide]({% url "docs" "user_pathways/researcher" %}).


# Commercial Licensing {: class="subtitle" }

In addition, under our agreement with Ravel (now owned by Lexis-Nexis), Ravel must negotiate in good faith to provide 
bulk access to anyone seeking to make commercial use of this data. 
[Click here to contact Ravel for more information](http://info.ravellaw.com/contact-us-form) or 
[contact us]({% url "contact" %}) and we will put you in touch with Ravel.


# User Types and Permissions {: class="subtitle" }

Unregistered Users
{: class="topic-header", id="def-unregistered-user" }

* Access all metadata
{: class="list-group-item" add_list_class="parameter-list" }
* Unlimited API access to all cases from [whitelisted]({% url 'docs' 'user_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }
* Bulk Download all cases from [whitelisted]({% url 'docs' 'user_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }

Registered Users
{: class="topic-header", id="def-registered-user" }

* Access all metadata
{: class="list-group-item" add_list_class="parameter-list" }
* Unlimited API access to all cases from [whitelisted]({% url 'docs' 'user_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }
* Access to 500 cases per day from non-[whitelisted]({% url 'docs' 'user_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }
* Bulk Download all cases from [whitelisted]({% url 'docs' 'user_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }


Researchers
{: class="topic-header", id="def-researchers" }

* Access all metadata
{: class="list-group-item" add_list_class="parameter-list" }
* Unlimited API access to all cases
{: class="list-group-item" add_list_class="parameter-list" }
* Bulk Downloads from all jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }

Commercial Users
{: class="topic-header", id="def-researchers" }

[Click here to contact Ravel for more information.](http://info.ravellaw.com/contact-us-form)
{: class="mt-0" }
