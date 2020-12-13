# project-2-04

## Login 
We incorported python social auth which requires all users to login before accessing the Study Buddy application. Once users have logged in successfully they will be redirected to the settings page where they can update their personal profile, course, and availability information.

## Settings
The settings page includes all of the user's personal profile, course, and availability information. This includes their name, email, classes, availability, and timezone which can all be updated/changed from this page. From here, a user can access the other three tabs to manage, create, and join groups and can also create and manage events for themselves.

## Get Matched
The Get Matched page is where users can go to run the matching algorithm we created. Initially this page will prompt you to add your courses if you haven't already done so. Once a user has filled out their courses and availability on the settings page, they can select a course to be matched with. The matching algorithm takes into account a user's availability, comfort level with course topics, time zone, and course to find groups that are the most compatable. 

Once the form is submitted the user will be taken to a results page. If there are groups available, they will come up at the top with the results from the matching algorithm in terms of overall compatability of the group, comfort levels in areas you might be lacking, and similar availability for group members. Users will then have the option to join one of these groups or create their own group.

If there are no groups available users will be asked if they would like to create a new group.

## Groups
The Groups tab is where all of a user's groups and invites are managed. At the top there is a list of pending invites from other groups that the user can either accept or decline. Under that is a list of all the user's groups where they can see the corresponding class and other users in the group while also having the ability to invite other users to that group or leave the group. Additionally, we incorporated the GroupMe API to allow users to create GroupMes for their groups. Once a GroupMe is created by one user, the rest of the users can join the GroupMe from this tab.

## Schedule
The Schedule tab is where individual users can create and manage events for themselves. Once the form is filled out the corresponding events will be listed in chronological order.

## Project Requirements
In terms of the project requirements we were able to meet all of them in some way with our Web Application. Users are able to save their courses from the settings page. Users are also able to change their comfort level to indicate where they need help and where they feel more comfortable to help others. In terms of matching groups, the system automatically generates compatable study groups, but also gives users the ability to create their own and then invite other users. Lastly, our system provides GroupMe as a mechanism to meet virtually with groups in order to communicate with group members.
