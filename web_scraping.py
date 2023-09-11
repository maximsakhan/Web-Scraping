#!/usr/bin/env python
# coding: utf-8

# In[1]:


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time
import re
from bs4 import BeautifulSoup
import pandas as pd


# In[2]:


# Define the path to the Firefox driver executable
driver_path = 'bin/geckodriver.exe'

# Set up the WebDriver service using the defined path
service = Service(executable_path=driver_path)

# Configure Firefox options
firefox_options = webdriver.FirefoxOptions()

# Enable headless mode to run Firefox without a visible browser window
firefox_options.add_argument("--headless")

# Create a new instance of the Firefox WebDriver with the specified service and options
driver = webdriver.Firefox(service=service, options=firefox_options)


# In[3]:


# Start from the main page of the website
main_page_url = "https://www.realcanadiansuperstore.ca/"
driver.get(main_page_url)

# Make sure the webdriver waits for the page to load the nav bar
wait = WebDriverWait(driver, 100)
element_present = wait.until(EC.visibility_of_element_located(
    (By.CLASS_NAME, 'primary-nav__list__item__link__text')))
# Find the nav bar element and click so it reveals the menu
dropdown_trigger = driver.find_element(By.CLASS_NAME, 'primary-nav__list__item__link__text')
dropdown_trigger.click()
actions = ActionChains(driver)

# Create a list to store category page URLs
category_page_urls = []

# Find all the main menu items
main_menu_items = wait.until(EC.presence_of_all_elements_located((
    By.CLASS_NAME, "primary-nav__list__item--with-children")))

# Iterate through menu items, hover to reveal submenus, scrape submenu URLs, and add them to a list
for main_menu_item in main_menu_items[:15]:
    main_menu_item_link = main_menu_item.find_element(By.CSS_SELECTOR, 'a.primary-nav__list__item__link')
    actions.move_to_element(main_menu_item_link).perform() 
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    nav_bar_columns = soup.find('div', class_='nav-columns')
    for column in nav_bar_columns:
        # Ignore bald letter menu links (they contain the same grouped category urls)
        nav_bar_link = column.find('a', href = True, 
                                   attrs={'style': lambda x: x is None or ('min-height: 0px;' not in x)})
        if nav_bar_link is not None: 
            # Ignore underlined submenu items
            nav_bar_span = nav_bar_link.find('span', style='text-decoration: underline;')
            if nav_bar_span is None:
                if 'seasonal-shop' not in nav_bar_link.get('href'):
                    # Ignore the seasonal shop menu (its items will be found through category urls)
                    full_nav_bar_link = f"https://www.realcanadiansuperstore.ca{nav_bar_link.get('href')}"
                    category_page_urls.append(full_nav_bar_link)


# In[8]:


# Initialize the empty lists
product_list = []
page_numbers = []

# Iterate through page urls, extract number of pages, scrape data from each page, append item data to list
for category_page_url in category_page_urls:
    # Navigate to the URL
    driver.get(category_page_url)
    # Ensure driver waits for each url to load elements
    element_present = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'css-19o1wu6')))
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    page_buttons = soup.find_all('button', class_='css-1cr7bzs')
    # Extract the number of pages from each url
    if len(page_buttons) > 0:
        max_page_number = max(int(button.get_text()) for button in page_buttons)
    else:
        max_page_number = 1
    for page_number in range(1, max_page_number + 1):
        # Cycle through each page of the url and get each page's content
        if page_number != 1:
            url = f"{category_page_url}&page={page_number}"  # Construct the URL
            driver.get(url)
            element_present = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'css-19o1wu6')))
            soup = BeautifulSoup(driver.page_source, 'html.parser')   
        # Extract the relevant data from the page like item name, price, etc.
        elements = soup.findAll('div', class_='css-wbarzq')
        category_name = soup.find('h1', class_='chakra-heading css-mf9l49').text
        if len(elements) > 0:
            for element in elements:
                name = element.find('h3', class_='chakra-heading css-1x14pul').text
                current_price = element.find('p', class_=['chakra-text css-1hj0zgu', 'chakra-text css-qwrgkt']).text
                previous_price = element.find('p', class_=['chakra-text css-1hj0zgu', 'chakra-text css-ijf5uj']).text
                price_per_each = element.find('p', class_='chakra-text css-1epbo8m').text
                product_id = element.find('a', class_='chakra-linkbox__overlay css-1hnz6hu')['href'][-14:]
                item_url = element.find('a', class_='chakra-linkbox__overlay css-1hnz6hu')['href']
                item_url = f"https://www.realcanadiansuperstore.ca{item_url}"  # Full item URL
                product_list.append((name, current_price, previous_price, price_per_each, category_name, product_id, item_url))

# Close the WebDriver
driver.quit() 


# In[9]:


# Define the column titles for the DataFrame
col_titles = ['Name', 'Current Price', 'Previous Price', 'Price Per Each', 'Category', 'Product ID', 'Product URL']

# Create a DataFrame using the product_list data and the specified column titles
raw_df = pd.DataFrame(product_list, columns=col_titles)
raw_df.to_csv('products_raw_data.csv', index=False, encoding='utf-8') # Save to CSV


# In[10]:


raw_df.head()


# In[11]:


# Load the raw data into a DataFrame
df = raw_df

# Clean the 'Product ID' column by removing '/p/'
df['Product ID'] = df['Product ID'].str.replace('/p/', '')

# Clean the 'Current Price' and 'Previous Price' columns
df['Current Price'] = df['Current Price'].str.replace(r'about |\$|sale ', '', regex=True)
df['Previous Price'] = df['Previous Price'].str.replace(r'about |\$|was', '', regex=True)

# Define a function to extract amount and units from 'Price Per Each'
def extract_amount_unit(input_string_list):
    amount_unit = []
    for input_string in input_string_list:
        if re.search(r'\d*?x?\d*?\.?\d+\s[A-Za-z]+\s?[A-Za-z]*?,\s*', input_string) is not None:
            # Use regex to find amount and unit
            match = re.search(r'(\d*\.?\d+x?\d*\.?\d*)\s?([A-Za-z]+)?', input_string)
            amount = match.group(1)
            unit = match.group(2) if match.group(2) else 'ea'
            amount_unit.append((amount, unit))
        else:
            # If the pattern doesn't match, assume '1 ea'
            amount_unit.append((1, 'ea'))
    return amount_unit

# Extract amount and unit into separate columns and add them to the DataFrame
amount_unit_cols = pd.DataFrame(extract_amount_unit(df['Price Per Each']), columns=['Amount', 'Units'])
df = pd.concat([df, amount_unit_cols], axis=1)

# Remove amount and unit from the 'Price Per Each' column
df['Price Per Each'] = df['Price Per Each'].str.replace(r'\d*\.?\d*x?\d*\.?\d*\s?[A-Za-z]+\s?[A-Za-z]*?,\s*', '', regex=True)

# Add a comma separator between multiple prices in the 'Price Per Each' column
df['Price Per Each'] = df['Price Per Each'].str.replace(r'\s', ', ', regex=True)


# In[14]:


df.head()


# In[13]:


df.to_csv('products_data.csv', index=False, encoding='utf-8') # Save to CSV

