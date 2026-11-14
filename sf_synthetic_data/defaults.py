"""Built-in Salesforce-style fields, picklists, and fictional source values."""

from __future__ import annotations

from typing import Any


PRESETS: dict[str, list[str]] = {
    "account": [
        "Id", "Name", "AccountNumber", "Type", "Industry", "AnnualRevenue", "CurrencyIsoCode",
        "NumberOfEmployees", "Phone", "Website", "BillingStreet", "BillingCity",
        "BillingState", "BillingPostalCode", "BillingCountry", "OwnerId",
        "Sales_Region__c", "Sales_District__c", "CreatedDate", "LastModifiedDate",
    ],
    "opportunity": [
        "Id", "Name", "AccountId", "OwnerId", "StageName", "Amount", "CurrencyIsoCode", "Probability",
        "CloseDate", "IsClosed", "IsWon", "ForecastCategoryName", "Type", "LeadSource",
        "NextStep", "Description", "Sales_Region__c", "Sales_District__c",
        "Closed_Won_Amount__c", "Closed_Lost_Amount__c", "Open_Pipeline_Amount__c",
        "CreatedDate", "LastModifiedDate",
    ],
    "contact": [
        "Id", "AccountId", "FirstName", "LastName", "Title", "Department", "Email",
        "Phone", "MobilePhone", "MailingStreet", "MailingCity", "MailingState",
        "MailingPostalCode", "MailingCountry", "LeadSource", "OwnerId",
        "Sales_Region__c", "Sales_District__c", "CreatedDate", "LastModifiedDate",
    ],
    "lead": [
        "Id", "FirstName", "LastName", "Company", "Title", "Email", "Phone", "Status",
        "LeadSource", "Industry", "AnnualRevenue", "NumberOfEmployees", "Street", "City",
        "State", "PostalCode", "Country", "OwnerId", "IsConverted", "ConvertedDate",
        "Sales_Region__c", "Sales_District__c", "CreatedDate", "LastModifiedDate",
    ],
    "case": [
        "Id", "CaseNumber", "AccountId", "ContactId", "OwnerId", "Subject", "Description",
        "Status", "Priority", "Origin", "Type", "Reason", "IsClosed", "CreatedDate",
        "ClosedDate", "Sales_Region__c", "Sales_District__c", "LastModifiedDate",
    ],
    "user": [
        "Id", "Username", "FirstName", "LastName", "Name", "Email", "Title", "Department",
        "IsActive", "UserRoleId", "ManagerId", "Sales_Region__c", "Sales_District__c",
        "CreatedDate", "LastModifiedDate",
    ],
}


DEFAULT_CONFIG: dict[str, Any] = {
    "regions": {
        "AMER": ["West", "Central", "East", "Canada", "LATAM"],
        "EMEA": ["UKI", "DACH", "France", "Benelux", "Nordics", "Southern Europe", "MEA"],
        "APAC": ["ANZ", "Japan", "India", "Southeast Asia", "Greater China"],
    },
    "opportunity_stages": [
        {"name": "Prospecting", "probability": 10, "weight": 14, "is_closed": False, "is_won": False, "forecast": "Pipeline"},
        {"name": "Qualification", "probability": 25, "weight": 18, "is_closed": False, "is_won": False, "forecast": "Pipeline"},
        {"name": "Needs Analysis", "probability": 40, "weight": 15, "is_closed": False, "is_won": False, "forecast": "Best Case"},
        {"name": "Proposal/Price Quote", "probability": 60, "weight": 14, "is_closed": False, "is_won": False, "forecast": "Best Case"},
        {"name": "Negotiation/Review", "probability": 80, "weight": 13, "is_closed": False, "is_won": False, "forecast": "Commit"},
        {"name": "Closed Won", "probability": 100, "weight": 16, "is_closed": True, "is_won": True, "forecast": "Closed"},
        {"name": "Closed Lost", "probability": 0, "weight": 10, "is_closed": True, "is_won": False, "forecast": "Omitted"},
    ],
    "lead_statuses": ["New", "Working", "Nurturing", "Qualified", "Unqualified"],
    "case_statuses": ["New", "Working", "Escalated", "Closed"],
    "industries": [
        "Financial Services", "Technology", "Healthcare", "Retail", "Manufacturing",
        "Telecommunications", "Energy", "Media", "Transportation", "Public Sector",
    ],
    "account_types": ["Prospect", "Customer - Direct", "Customer - Channel", "Partner", "Competitor"],
    "lead_sources": ["Web", "Partner Referral", "Trade Show", "Outbound", "Advertisement", "Employee Referral"],
    "opportunity_types": ["New Business", "Existing Business", "Renewal", "Upsell", "Cross-sell"],
    "case_types": ["Problem", "Question", "Feature Request", "Incident"],
    "currencies": ["USD", "EUR", "GBP"],
}


FIRST_NAMES = [
    "Alex", "Amara", "Amina", "Ana", "Ben", "Camila", "Chen", "Daniel", "Diego", "Elena",
    "Emma", "Fatima", "Grace", "Hana", "Haruto", "Isabella", "Jack", "James", "Javier", "Jordan",
    "Kai", "Leila", "Liam", "Lucia", "Maya", "Mei", "Mia", "Mohammed", "Noah", "Oliver",
    "Priya", "Ravi", "Sofia", "Sora", "Theo", "Yuki", "Zara",
]

LAST_NAMES = [
    "Adams", "Ahmed", "Andersson", "Brown", "Campbell", "Chen", "Costa", "Dubois", "Evans",
    "Garcia", "Gupta", "Hernandez", "Ito", "Johnson", "Khan", "Kim", "Kowalski", "Lee",
    "Martin", "Miller", "Murphy", "Nakamura", "Nguyen", "Patel", "Rossi", "Schmidt", "Silva",
    "Singh", "Smith", "Taylor", "Thomas", "Wang", "Wilson", "Yamamoto",
]

COMPANY_WORDS = [
    "Apex", "Atlas", "Aurora", "Blue", "Bright", "Cedar", "Cloud", "Core", "Crown", "Delta",
    "Evergreen", "Global", "Harbor", "Horizon", "Iron", "Juniper", "Keystone", "Lighthouse",
    "Meridian", "Metro", "Nimbus", "Northstar", "Nova", "Oak", "Orion", "Peak", "Pioneer",
    "Quantum", "River", "Silver", "Summit", "Terra", "Unity", "Vertex", "Westbridge",
]

COMPANY_NOUNS = [
    "Analytics", "Capital", "Digital", "Dynamics", "Foods", "Health", "Industries", "Labs",
    "Logistics", "Media", "Networks", "Partners", "Retail", "Robotics", "Security", "Services",
    "Solutions", "Systems", "Technologies", "Telecom", "Ventures", "Works",
]

TITLES = [
    "Chief Executive Officer", "Chief Financial Officer", "Chief Information Officer",
    "Chief Revenue Officer", "VP Sales", "VP Operations", "Sales Director", "IT Director",
    "Head of Procurement", "Finance Director", "Operations Manager", "Product Manager",
    "Account Executive", "Business Development Manager", "Data Architect",
]

DEPARTMENTS = ["Executive", "Sales", "Finance", "Operations", "IT", "Procurement", "Marketing", "Product"]

ID_PREFIX = {
    "account": "001", "contact": "003", "user": "005", "opportunity": "006",
    "lead": "00Q", "case": "500", "campaign": "701", "userrole": "00E",
}

ALIASES = {
    "accountname": "Name", "opportunityname": "Name", "fullname": "Name",
    "accountid": "AccountId", "owner": "OwnerId", "ownerid": "OwnerId",
    "stage": "StageName", "opportunitystage": "StageName", "stagename": "StageName",
    "closed": "IsClosed", "isclosed": "IsClosed", "won": "IsWon", "iswon": "IsWon",
    "closedwonamount": "Closed_Won_Amount__c", "closedwonamountc": "Closed_Won_Amount__c",
    "closedlostamount": "Closed_Lost_Amount__c", "closedlostamountc": "Closed_Lost_Amount__c",
    "openpipelineamount": "Open_Pipeline_Amount__c", "openpipelineamountc": "Open_Pipeline_Amount__c",
    "salesregion": "Sales_Region__c", "salesregionc": "Sales_Region__c", "region": "Sales_Region__c",
    "salesdistrict": "Sales_District__c", "salesdistrictc": "Sales_District__c", "district": "Sales_District__c",
    "employees": "NumberOfEmployees", "numberemployees": "NumberOfEmployees",
    "created": "CreatedDate", "modified": "LastModifiedDate", "lastmodified": "LastModifiedDate",
}

LOCATION_BY_REGION = {
    "AMER": [
        ("United States", "California", "San Francisco"), ("United States", "New York", "New York"),
        ("United States", "Illinois", "Chicago"), ("Canada", "Ontario", "Toronto"),
        ("Brazil", "São Paulo", "São Paulo"), ("Mexico", "CDMX", "Mexico City"),
    ],
    "EMEA": [
        ("United Kingdom", "England", "London"), ("Germany", "Bavaria", "Munich"),
        ("France", "Île-de-France", "Paris"), ("Netherlands", "North Holland", "Amsterdam"),
        ("Sweden", "Stockholm", "Stockholm"), ("Spain", "Madrid", "Madrid"),
        ("United Arab Emirates", "Dubai", "Dubai"),
    ],
    "APAC": [
        ("Australia", "New South Wales", "Sydney"), ("Japan", "Tokyo", "Tokyo"),
        ("India", "Karnataka", "Bengaluru"), ("Singapore", "Singapore", "Singapore"),
        ("South Korea", "Seoul", "Seoul"), ("New Zealand", "Auckland", "Auckland"),
    ],
}
