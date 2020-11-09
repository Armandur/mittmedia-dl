# mittmedia-dl
Download latest issue from Mittmedias e-paper viewer, currently only for subscribers to Tidingen Ångermanland, though should be able to make it more general for all Mittmedias publications.

## Required libs:
* selenium
* requests
* PyPDF2

**Firefox driver for selenium (geckodriver) is required to be in PATH**

## Usage:
    mittmedia-dl.py Login-Email Password Token
	

### To get token:
Open a newspaper in viewer with developer tools active and view requests to https://contentcdn.textalk.se/api/v2/
Copy token *"x-textalk-content-client-authorize"*

Token is persistent, but unique for each newspaper
