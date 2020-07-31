library(tidyverse)
library(sf)
library(opendatatoronto)
library(viridis)

# Rent Data ---------------------------------------------------------------
rent_data_loader <- function(){
  rent_data <- read_csv("RCSV Files/rent_data.csv")
  View(rent_data)
  return(rent_data)
}
# Important Function -------------------------------------------------

data_pipeline <- function(){
  rent_data <- rent_data_loader()
  toronto_data_points_cleaned <- data_cleaner(rent_data)
  return(toronto_data_points_cleaned)
}
# Data Loader -------------------------------------------------------------

neighbourhood_data_loader <- function(){

  # get package
  package <- show_package("4def3f65-2a65-4a4f-83c4-b2a4aed72d46")
  package
  
  # get all resources for this package
  resources <- list_package_resources("4def3f65-2a65-4a4f-83c4-b2a4aed72d46")
  
  # identify datastore resources; by default, Toronto Open Data sets datastore resource format to CSV for non-geospatial and GeoJSON for geospatial resources
  datastore_resources <- filter(resources, tolower(format) %in% c('csv', 'geojson'))
  
  # load the first datastore resource as a sample
  neighbourhoods <- filter(datastore_resources, row_number()==1) %>% get_resource()
  neighbourhoods
  
  return(neighbourhoods)
}

# Data Cleaning ----------------------------------------------------------

data_cleaner <- function(df){

  toronto_data_points <- data.frame (longitude = df$lng, latitude = df$lat, price = df$Price)
  
  toronto_data_points_cleaned <- toronto_data_points %>%
  filter(longitude >= -79.65 & longitude <= -79.12 & 
           latitude >= 43.58  & latitude <= 43.85 &
           !is.na(longitude) &
           !is.na(latitude))
  
  return (toronto_data_points_cleaned)
}

# Rental Property Cartisian Coordinates ----------------------------------

toronto_rent_coord <- function(df){
  toronto.sf.point <- st_as_sf(df, 
                               coords = c("longitude", "latitude"))
  return(toronto.sf.point)
}
# Toronto Rent Normally Distrubuted --------------------------------------

toronto_plot_maker <- function(df){
  toronto_plot_points <- df %>%
    filter(price < (mean(price) + 2 * sqrt(var(price)))) 
  return(toronto_plot_points)
}

# Toronto Rent Map (No Outliers)------------------------------------------

toronto_map_plot <- function(nbhd_df,data_df){
  ggplot(data = nbhd_df$geometry) +
    geom_sf() + 
    geom_point(data = data_df, aes( x=longitude, y = latitude, 
                colour = price), shape = 19) + 
    scale_color_viridis() +
    ggtitle("Rent Data on Toronto Map (No Outliers)")
}
 