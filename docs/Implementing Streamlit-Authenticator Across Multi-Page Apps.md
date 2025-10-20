# Implementing Streamlit-Authenticator Across Multi-Page Apps

Streamlit-Authenticator allows you to add a simple yet robust method for user authentication in a Streamlit application.

[Brian Roepke](https://towardsdatascience.com/author/broepke/)

Nov 23, 2024

7 min read

Share

![AI Generated Image by Author using HubSpot AI](https://towardsdatascience.com/wp-content/uploads/2024/11/0nCQnY7aEHHigxeHr.jpeg)AI Generated Image by Author using HubSpot AI

## Introduction

Streamlit is a widely used tool for creating quick web applications backed by data, but one of the capabilities it does not have is the ability to manage multiple users and identify them while they use the app.

Streamlit has some basic [documentation](https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso) on how you can add this by using hard coded key-value pairs in your `secrets.toml` file, however this is a really simplistic method and you’ll probably outgrow it quickly!

Fortunately, developer Mohammad Khorasani wrote an excellent package that adds pretty sophisticated authentication in a very simple and elegant way! It’s called [Streamlit Authenticator](https://github.com/mkhorasani/Streamlit-Authenticator) and is available on GitHub and can be installed with your favorite package manager, such as PIP.

Mohammad supplies a nice [sample application](https://demo-app-v0-3-3.streamlit.app/) and code for a single-page application, but there is not one for a multi-page application. I decided to make a starting point for anyone that is interested in using it. I also [checked](https://github.com/mkhorasani/Streamlit-Authenticator-demo/issues/1) with the author to make sure the code was correct.

Here is the [complete code](https://github.com/broepke/streamlit-auth-test-app) for your starter application if you want to dive right in.

![Image by Author](https://towardsdatascience.com/wp-content/uploads/2024/11/0j1k44N5rdpuhBFd9.png)Image by Author

## Challenges with Multi-Page Apps

The main issue you’ll find with Multi-Page applications is that you need to properly manage the Streamlit Session State. After you log in, you need to persist the authentication information properly, check to make sure that the user is logged in, and in turn present the correct information.

> Please remember to pass the authenticator object to each and every page in a multi-page application as a session state variable.

There are a few notes in the documentation, such as the above, about multi-page apps but not really enough to easily get you up-and-running.

## Setting Up the Initial Authenticator

Start by creating the `Home.py` file that will be the application entry point. We need our standard imports and some basic code to rough out the Streamlit app.

```javascript
import streamlit as st
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities import LoginError
import yaml
from yaml.loader import SafeLoader

st.title("Streamlit-Authenticator")
```

Next, per the setup guide, we can add the required information to read the config.yaml file (see the [docs](https://github.com/mkhorasani/Streamlit-Authenticator?tab=readme-ov-file#3-creating-a-config-file) on how this all works).

```python
# Load credentials from the YAML file
with open("config.yaml") as file:
     config = yaml.load(file, Loader=SafeLoader)

# Initialize the authenticator
authenticator = stauth.Authenticate(
     config["credentials"],
     config["cookie"]["name"],
     config["cookie"]["key"],
     config["cookie"]["expiry_days"],)
```

And next, we need to set up the session state per the quote above from the documentation. Here is how we accomplish this.

```python
# Store the authenticator object in the session state
st.session_state["authenticator"] = authenticator
# Store the config in the session state so it can be updated later
st.session_state["config"] = config
```

Notice that in addition to the **authenticator object**, we’re storing the **config** that we read from the file above. This allows us to write that out at a later time if and when the config file has been updated, such as changing a password. Finally, we render the login widget and add logic to determine if the user is logged in or not.

I want to also point out the **logout button** being rendered in the sidebar when the user is logged in. The important step here is to make sure the `key=` has a unique name for every page. Keep this simple and use your app name and **append the page name** to the key’s value. This is true for the login widget as well.

> Unique key provided to widget to avoid duplicate WidgetID errors.

```python
# Authentication logic
try:
    authenticator.login(location="main", key="login-demo-app-home")
except LoginError as e:
     st.error(e)

if st.session_state["authentication_status"]:
     authenticator.logout(location="sidebar", key="logout-demo-app-home")
elif st.session_state["authentication_status"] is False:
     st.error("Username/password is incorrect")
elif st.session_state["authentication_status"] is None:
     st.warning("Please enter your username and password")
```

Let’s also look at what the session state looks like now that we’re logged in and have saved the above into session state. We have a few things right away that stand out. There is a key called logout-demo-app-home which represents the state of the logout button. There is our authenticator object stored as well as the config. Additionally, we have access to information about the user such as username, email, name, and roles. All of these are very useful for personalizing your application!

![Image by Author](https://towardsdatascience.com/wp-content/uploads/2024/11/0KqUw1d2puCWJ_cMm.png)Image by Author

## Setting Up all Additional Pages

Now for the good part: Getting this to work seamlessly on subsequent pages in your application. Create a new file in a folder called `pages` and name it it appropriately for your functionality. I’ll keep this simple and name it `Page_1.py`. Let’s start with our imports and basic Streamlit code. Notice that we don’t have to directly import any of the Authenticator packages since we’re only going to be using the session state’s information.

```python
import streamlit as st
import yaml

st.set_page_config(page_title="Page 1")
st.title("Page 1")
```

And then before we render any page information, we can check to see if the user is authenticated. There is a **top level key** in the **session state** called `authentication_status` which is a `boolean`. We can simple check to see if is is `true`, and in turn retrieve the authenticator object from the session state.

One of the tips the developer has is that for each page you need to **call the login widget**, but this time without rendering it. You additionally will give this a new, unique key-value that will help with session collisions as you navigate pages.

```python
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    authenticator.logout(location="sidebar", key="logout-demo-app-page-1")
    authenticator.login(location="unrendered", key="authenticator-page-1")
    # Put the main code and logic for your page here.
    st.success("You are logged in!")

elif st.session_state == {} or st.session_state["authentication_status"] is None:
    st.warning("Please use the button below to navigate to Home and log in.")
    st.page_link("Home.py", label="Home", icon=" ")
    st.stop()
```

If the user was not authenticated, get them to head back to the **home page** and log in. This code can be easily repeated on every page you have. Just remember to give all of the keys unique values.

![Image by Author](https://towardsdatascience.com/wp-content/uploads/2024/11/0Ec1sThalQGV1E7nE.png)Image by Author

## Bonus: Admin Role & Tools

The developer recently added the concept of Roles to the application. These come in the form of a simple configuration with a set of strings that really can be anything you’d like. Something for you to separate out functionality. Here is a user with three roles attached to it.

```yaml
credentials:
     usernames:
         brian:
             email: brian@example.com
              failed_login_attempts: 0
              first_name: Brian
              last_name: Roepke
              logged_in: false
              password: <<hashed-pw>>
              roles:
                  - admin
                  - editor
                  - viewer
```

The beauty of this is that the roles will show up at the top level of the session state, and the roles for that user will be returned as a simple list of values.

![Image by Author](https://towardsdatascience.com/wp-content/uploads/2024/11/0NMZfDkQXSdWXe5BS.png)Image by Author

Based on that, we can write some simple code that checks the session state for the roles value and then subsequently checks to see if admin is in the available values. Simple as that!

```python
try:
     user_roles = st.session_state.get("roles", []) or []

     if "admin" in user_roles:
         st.subheader("Admin Tools")

         # Implement anything you like here that is Admin only

except Exception as e:
     st.error(f"An error occurred: {e}")
```

In my application, I chose to create a simple utility that allows me to download the configuration data as a file in case it was updated, and finally, a printout of the session state should I need to inspect it.

![Image by Author](https://towardsdatascience.com/wp-content/uploads/2024/11/0u4ib_Go0_d2Qcl5b.png)Image by Author

Here again is the [complete code](https://github.com/broepke/streamlit-auth-test-app) for your starter application.

## Conclusion

In conclusion, integrating Streamlit Authenticator into your multi-page Streamlit application can simplify adding user management. By following the steps outlined in this guide, you can effectively manage authentication across different pages, ensuring a seamless user experience. The addition of roles further allows for tailored access and functionality, making your application more robust and versatile. With these tools and techniques, you’re well-equipped to build multi-user-friendly applications. Happy coding!