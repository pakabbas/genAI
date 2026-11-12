DrillDown Functional Requirements Document

1. Introduction	3
1.1 Purpose	3
1.2 Scope	3
1.2.1 In Scope	3
1.2.2 Out of Scope	3
1.3 Background	3
1.4 Assumptions and Constraints	3
2. Business Requirements	4
2.1 User Flow Diagrams	4
● 2.1.1: Account Creation and Authentication	4
● 2.1.2 Diagram Creation	5
2.2 Business Requirements	5
● BR1: Account Creation and Authentication	5
● BR2: Payment Platform	5
● BR3: Document Creation	5
● BR4: AI Interface	6
● BR5: Canvas Behavior Requirements	6
● BR6: Drill Downs	7
● BR7: Saving, Sharing, and Publishing	7
3. Functional Requirements	8
3.1 System Diagram	8
3.2 Functional Requirements	8
4. Data Requirements	8
4.1 Data Flow Diagram	8
4.2 Data Dictionary	8
5. System Integration Requirements	8
5.1 User-Facing Integrations	8
5.2 Internal/Back End Integrations	8


Introduction
1.1 Purpose
The Purpose of this FRD is to define the requirements for rebuilding the existing DrillDown product functionality within the Spiralloops environment to enable easier development and integration. This version is intended for potential investors, focus groups, and beta users.
1.2 Scope
1.2.1 In Scope
The Scope of this document will address all business and functional requirements needed to develop a working product that is suitable for release and customer use. This will include all basic functionality within the product itself.
1.2.2 Out of Scope
This FRD will not address the requirements for feature enhancement or expansion, including integrations with external systems/software (excluding account management features; see 1.4), or any future enhancements not deemed by the design team to be part of the Minimum Viable Product intended to go to market.
1.3 Background
This document will represent the core vision of the Drilldown product and its basic functionality, so that the lead designer and lead developer have a clear set of instructions on the expectations for how the product will look and function. The goals of this document are to outline the purposes behind each set of functional requirements, as well as clearly define how each feature should work in order to satisfy these business requirements.
1.4 Assumptions and Constraints
All existing features currently on the DrillDown platform will be duplicated within the Spiralloops environment
Once product is ready for release, product will be moved off Spiralloops platforms and on to DrillDown platforms
AI features and integrations with existing functionality are included in this scope
Account creation and management, including Google SSO and payment integration, will be included in this release


Business Requirements
2.1 User Flow Diagrams
2.1.1: Account Creation and Authentication


2.1.2 Diagram Creation

2.2 Business Requirements
BR1: Account Creation and Authentication
Users must be able to create an account with a valid email address
Users must be able to log in to DrillDown with their established credentials
Google SSO may be used as an alternate method of creating accounts/login
BR2: Payment Platform
Subscription level must be selected at time of account creation
The first five licenses are a free subscription and no payment information is required for these users
Users wishing to change their subscription level must be able to do so from their account page/dashboard
Users attempting to upgrade from a free to a paid subscription should be prompted for credit card information
BR3: Document Creation
BR3.1: Document Creation from Blank Canvas
Users with edit permissions must be able to create a new document.
Users without edit permissions cannot create a new document.
BR3.2: Document Creation via AI
Users with edit permissions can select the option to use the AI interface to create their document
BR4: AI Interface
The How-To tutorial pop up should appear when a user selects the Document Creation via AI option
User should be able to select “do not show again” option, at which point this pop up will not appear during subsequent AI diagram creation sessions
The AI interface will allow users to create a draft diagram based on prompts submitted to the integrated AI agent
The AI agent will ask clarifying questions if it does not have enough information to create a diagram
The AI agent will update the diagram based on feedback and edits provided by the user
The AI interface will support basic types of diagrams as specified below and their associated standard shapes:
Swimlane/BPMN
Flowchart Diagram
Time and resources permitting, the following diagram types will be implemented in order:
Use Case Diagram
Entity Relationship Diagram
Sequence Diagram
Class Diagram
Network Diagram
Architecture Diagram
Once a diagram has been created to the satisfaction of the user, the user will be able to export this image directly into the DrillDown tool as it appears in the AI interface
BR5: Canvas Behavior Requirements
BR5.1: Add a step
Users must be able to add a step, represented by one of the standard process flow shapes, to their document
BR5.2: Insert a step
Users must be able to add a step in between two existing steps
When users drop the shape in between the existing steps, the interface must be adaptive enough to shift all content on either side of the added step while still maintaining the existing spacing and alignment 
BR5.3: Delete a step
Users must be able to delete an existing step
If the deleted step exists between two other steps, the interface must be adaptive enough to shift all content on either side of the added step while still maintaining the existing spacing and alignment
BR5.4: Snap to grid
In order to minimize the time spent by users re-arranging the diagram for purely aesthetic reasons, the interface must have a “snap to grid” function, which will force 90 degree angles and prevent diagonal or uneven lines.
In order to prevent limiting functionality unnecessarily, the Snap to Grid functionality must be a feature that can be toggled off and on
For the MVP version of this product, activating or deactivating this toggle does not need to apply to the content currently in the document, only the addition of new steps.
BR6: Drill Downs
BR6.1: Add a Drill Down section
Users must be able to add a drill down section to their document by selecting the shape(s) and/or line(s) to which their information applies and selecting an “add drill down” option.
Users must be able to select multiple shapes/lines to create a single Drill Down (functionality currently works by holding CTRL while selecting)
Users must be able to specify a category and label color for their Drill Down
System should remember a user’s categories and label colors to minimize data errors and confusion
User should be able to delete a drilldown label in the event of an error/typo/duplicate 
BR6.2: Edit a Drill Down section
Users must be able to edit the text content, label, and color of their existing drill down sections.
For the MVP version of this product, it is not required that users be able to edit the shapes/lines to which their existing drill down section pertains, only the content within.
BR6.3: Delete a Drill Down section
Users must be able to delete a drill down section for which they have edit permissions
BR7: Saving, Sharing, and Publishing 
BR7.1: Save the document
Users must be able to save their document so that they can access it later
BR7.2: Authors
The user who creates a document will have the permission level “author”
Authors are able to edit the document’s content, delete the document permanently, and add other Collaborators (See BR7.3)
BR7.3: Add a Collaborator
Users must be able to add a collaborator to their document. There is no limit to the number of users with Collaborator permissions.
Collaborators should be able to edit the document. Only existing users who have edit permissions within the product should be able to be added as collaborators. Interface should display an error if user attempts to add an editor without edit permissions.
BR7.4: Add a Viewer
Users must be able to add a viewer to this document. There is no limit to the number of users with view permission.
Viewers should be able to view all aspects of the document. No edit functionality. Available to all registered users.

Functional Requirements
3.1 System Diagram
3.2 Functional Requirements
Data Requirements
4.1 Data Flow Diagram
4.2 Data Dictionary
System Integration Requirements
5.1 User-Facing Integrations
5.2 Internal/Back End Integrations


