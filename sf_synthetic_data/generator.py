"""Deterministic Salesforce-style record generation."""

from __future__ import annotations

import hashlib
import math
import random
import re
import string
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterable

from .config import validate_config, validate_filters
from .defaults import (
    ALIASES,
    COMPANY_NOUNS,
    COMPANY_WORDS,
    DEPARTMENTS,
    FIRST_NAMES,
    ID_PREFIX,
    LAST_NAMES,
    LOCATION_BY_REGION,
    PRESETS,
    TITLES,
)


@dataclass(frozen=True)
class Stage:
    name: str
    probability: int | float
    weight: float
    is_closed: bool
    is_won: bool
    forecast: str


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def canonical_field(column: str) -> str:
    key = normalize(column)
    if key in ALIASES:
        return ALIASES[key]
    for fields in PRESETS.values():
        for field in fields:
            if normalize(field) == key:
                return field
    return column.strip()


def parse_columns(text: str) -> list[str]:
    columns = [part.strip() for part in re.split(r"[,;\t\n]+", text) if part.strip()]
    if not columns:
        raise ValueError("no columns were supplied")
    duplicates = sorted({column for column in columns if columns.count(column) > 1})
    if duplicates:
        raise ValueError(f"duplicate columns: {', '.join(duplicates)}")
    return columns


def stable_seed(seed: int, *parts: object) -> int:
    value = ":".join([str(seed), *(str(part) for part in parts)])
    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:8], "big")


def base36(number: int, width: int = 15) -> str:
    alphabet = string.digits + string.ascii_uppercase
    chars = []
    while number:
        number, remainder = divmod(number, 36)
        chars.append(alphabet[remainder])
    return ("".join(reversed(chars)) or "0").rjust(width, "0")[-width:]


def sf_id(object_name: str, number: int) -> str:
    """Return a Salesforce-style 18-character ID with the standard checksum."""
    id15 = ID_PREFIX.get(object_name, "a00") + base36(number, width=12)
    checksum_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
    suffix = ""
    for start in range(0, 15, 5):
        flags = sum(1 << offset for offset, char in enumerate(id15[start : start + 5]) if char.isupper())
        suffix += checksum_alphabet[flags]
    return id15 + suffix


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower()) or "example"


def iso_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def weighted_choice(rng: random.Random, values: list[Any], weights: list[float]) -> Any:
    return rng.choices(values, weights=weights, k=1)[0]


class SalesforceGenerator:
    def __init__(
        self,
        object_name: str,
        rows: int,
        config: dict[str, Any],
        seed: int,
        region_filter: set[str] | None = None,
        district_filter: set[str] | None = None,
        as_of_date: date | None = None,
        scale_reference_pools: bool = True,
    ) -> None:
        if object_name not in PRESETS:
            raise ValueError(f"unknown object '{object_name}'; choose from: {', '.join(PRESETS)}")
        if isinstance(rows, bool) or not isinstance(rows, int) or rows < 1:
            raise ValueError("rows must be at least 1")
        validate_config(config)
        self.object_name = object_name
        self.rows = rows
        self.config = config
        self.seed = seed
        self.rng = random.Random(seed)
        self.today = as_of_date or date.today()
        self.now = datetime.combine(self.today, time(23, 59, 59), tzinfo=timezone.utc)
        self.region_map = validate_filters(config, region_filter, district_filter)
        self.stages = [Stage(**stage) for stage in config["opportunity_stages"]]
        owner_count = max(12, min(200, math.ceil(rows / 150))) if scale_reference_pools else 12
        account_count = max(100, math.ceil(rows / 4)) if scale_reference_pools else 100
        contact_count = max(100, math.ceil(rows / 3)) if scale_reference_pools else 100
        self.owner_pool = [sf_id("user", i + 1) for i in range(owner_count)]
        self.account_pool = [sf_id("account", i + 1) for i in range(account_count)]
        self.contact_pool = [sf_id("contact", i + 1) for i in range(contact_count)]

    def _person(self) -> tuple[str, str]:
        return self.rng.choice(FIRST_NAMES), self.rng.choice(LAST_NAMES)

    def _company(self, index: int) -> str:
        return f"{self.rng.choice(COMPANY_WORDS)} {self.rng.choice(COMPANY_NOUNS)} {index:05d}"

    def _region(self) -> tuple[str, str]:
        region = self.rng.choice(list(self.region_map))
        return region, self.rng.choice(self.region_map[region])

    def _location(self, region: str) -> tuple[str, str, str, str, str]:
        country, state, city = self.rng.choice(LOCATION_BY_REGION.get(region, LOCATION_BY_REGION["AMER"]))
        number = self.rng.randint(1, 999)
        street = f"{number} {self.rng.choice(COMPANY_WORDS)} Street"
        postal = str(self.rng.randint(10000, 99999))
        return street, city, state, postal, country

    def _amount(self, rng: random.Random | None = None) -> float:
        source = rng or self.rng
        return round(min(10_000_000, max(1_000, source.lognormvariate(11.4, 1.05))), 2)

    def _context(self, index: int) -> dict[str, Any]:
        first, last = self._person()
        company = self._company(index)
        region, district = self._region()
        street, city, state, postal, country = self._location(region)
        created_date = self.today - timedelta(days=self.rng.randint(1, 730))
        created_dt = datetime.combine(created_date, time(self.rng.randint(7, 19), self.rng.randint(0, 59)), tzinfo=timezone.utc)
        modified_dt = min(self.now, created_dt + timedelta(days=self.rng.randint(0, 180)))
        stage = weighted_choice(self.rng, self.stages, [stage.weight for stage in self.stages])
        close_date = (
            max(created_date, self.today - timedelta(days=self.rng.randint(0, 365)))
            if stage.is_closed
            else max(created_date, self.today + timedelta(days=self.rng.randint(-30, 365)))
        )
        amount = self._amount()
        status = self.rng.choice(self.config["lead_statuses"])
        is_converted = status == "Qualified" and self.rng.random() < 0.72
        case_status = self.rng.choice(self.config["case_statuses"])
        return {
            "index": index,
            "first": first,
            "last": last,
            "company": company,
            "domain": slug(company) + ".example",
            "region": region,
            "district": district,
            "street": street,
            "city": city,
            "state": state,
            "postal": postal,
            "country": country,
            "created_date": created_date,
            "created_dt": created_dt,
            "modified_dt": modified_dt,
            "stage": stage,
            "close_date": close_date,
            "amount": amount,
            "lead_status": status,
            "is_converted": is_converted,
            "case_status": case_status,
            "owner_id": self.rng.choice(self.owner_pool),
            "account_id": self.rng.choice(self.account_pool),
            "contact_id": self.rng.choice(self.contact_pool),
        }

    def _name(self, context: dict[str, Any]) -> str:
        if self.object_name == "account":
            return context["company"]
        if self.object_name == "opportunity":
            offer = self.rng.choice(["Platform", "Analytics", "Cloud", "Security", "Expansion", "Renewal"])
            return f"{context['company']} - {offer}"
        return f"{context['first']} {context['last']}"

    def _fallback(self, field: str, context: dict[str, Any]) -> Any:
        key = normalize(field)
        rng = random.Random(stable_seed(self.seed, self.object_name, context["index"], field))
        if key.startswith(("is", "has")):
            return rng.random() < 0.5
        if key.endswith("date"):
            return (self.today + timedelta(days=rng.randint(-365, 365))).isoformat()
        if "amount" in key or "revenue" in key or "value" in key:
            return self._amount(rng)
        if "percent" in key or "probability" in key:
            return rng.randint(0, 100)
        if "count" in key or "number" in key or "quantity" in key:
            return rng.randint(0, 5000)
        if "email" in key:
            return f"{context['first']}.{context['last']}{context['index']}@{context['domain']}".lower()
        if "phone" in key:
            return f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}"
        if key.endswith("id"):
            return sf_id("custom", context["index"])
        return f"{field.replace('_', ' ').strip()} {context['index']:05d}"

    def _known_values(self, context: dict[str, Any]) -> dict[str, Any]:
        stage: Stage = context["stage"]
        amount = context["amount"]
        name = self._name(context)
        manager_id = self.rng.choice(self.owner_pool)
        role_id = sf_id("userrole", self.rng.randint(1, 25))
        title = self.rng.choice(TITLES)
        department = self.rng.choice(DEPARTMENTS)
        phone = f"+1-555-{self.rng.randint(100, 999)}-{self.rng.randint(1000, 9999)}"
        mobile_phone = f"+1-555-{self.rng.randint(100, 999)}-{self.rng.randint(1000, 9999)}"
        record_type = self.rng.choice(
            self.config["opportunity_types"] if self.object_name == "opportunity"
            else self.config["case_types"] if self.object_name == "case"
            else self.config["account_types"]
        )
        industry = self.rng.choice(self.config["industries"])
        annual_revenue = round(amount * self.rng.uniform(8, 80), 2)
        employees = max(2, int(self.rng.lognormvariate(5.0, 1.3)))
        lead_source = self.rng.choice(self.config["lead_sources"])
        currency = self.rng.choice(self.config["currencies"])
        subject = self.rng.choice(["Login issue", "Billing question", "Feature request", "Data import", "Performance issue", "Integration help"])
        priority = self.rng.choices(["Low", "Medium", "High"], weights=[35, 50, 15], k=1)[0]
        origin = self.rng.choice(["Web", "Email", "Phone", "Chat"])
        reason = self.rng.choice(["User education", "Configuration", "Bug", "Integration", "Billing"])
        is_active = self.rng.random() >= 0.06
        converted_date = min(self.today, context["created_date"] + timedelta(days=self.rng.randint(1, 90))).isoformat() if context["is_converted"] else ""
        is_closed = stage.is_closed if self.object_name == "opportunity" else context["case_status"] == "Closed"
        return {
            "Id": sf_id(self.object_name, context["index"]),
            "Name": name,
            "AccountId": context["account_id"],
            "ContactId": context["contact_id"],
            "OwnerId": context["owner_id"],
            "ManagerId": manager_id,
            "UserRoleId": role_id,
            "AccountNumber": f"ACCT-{context['index']:08d}",
            "CaseNumber": f"{context['index']:08d}",
            "FirstName": context["first"],
            "LastName": context["last"],
            "Company": context["company"],
            "Title": title,
            "Department": department,
            "Email": f"{context['first']}.{context['last']}{context['index']}@{context['domain']}".lower(),
            "Username": f"{context['first']}.{context['last']}.{context['index']}@synthetic.example".lower(),
            "Phone": phone,
            "MobilePhone": mobile_phone,
            "Website": f"https://www.{context['domain']}",
            "Type": record_type,
            "Industry": industry,
            "AnnualRevenue": annual_revenue,
            "NumberOfEmployees": employees,
            "LeadSource": lead_source,
            "Status": context["case_status"] if self.object_name == "case" else context["lead_status"],
            "StageName": stage.name,
            "Amount": amount,
            "CurrencyIsoCode": currency,
            "Probability": stage.probability,
            "CloseDate": context["close_date"].isoformat(),
            "IsClosed": is_closed,
            "IsWon": stage.is_won,
            "ForecastCategoryName": stage.forecast,
            "Closed_Won_Amount__c": amount if stage.is_won else 0.0,
            "Closed_Lost_Amount__c": amount if stage.is_closed and not stage.is_won else 0.0,
            "Open_Pipeline_Amount__c": amount if not stage.is_closed else 0.0,
            "NextStep": "Finalize commercial terms" if stage.probability >= 60 else "Confirm discovery and stakeholders",
            "Subject": subject,
            "Description": f"Synthetic {self.object_name} record for testing. Region: {context['region']}; district: {context['district']}.",
            "Priority": priority,
            "Origin": origin,
            "Reason": reason,
            "IsActive": is_active,
            "IsConverted": context["is_converted"],
            "ConvertedDate": converted_date,
            "CreatedDate": iso_datetime(context["created_dt"]),
            "LastModifiedDate": iso_datetime(context["modified_dt"]),
            "ClosedDate": context["close_date"].isoformat() if is_closed else "",
            "Sales_Region__c": context["region"],
            "Sales_District__c": context["district"],
            "BillingStreet": context["street"],
            "BillingCity": context["city"],
            "BillingState": context["state"],
            "BillingPostalCode": context["postal"],
            "BillingCountry": context["country"],
            "MailingStreet": context["street"],
            "MailingCity": context["city"],
            "MailingState": context["state"],
            "MailingPostalCode": context["postal"],
            "MailingCountry": context["country"],
            "Street": context["street"],
            "City": context["city"],
            "State": context["state"],
            "PostalCode": context["postal"],
            "Country": context["country"],
        }

    def generate(self, columns: list[str]) -> Iterable[dict[str, Any]]:
        canonical = [(column, canonical_field(column)) for column in columns]
        custom_fields = sorted({field for _, field in canonical if field not in PRESETS.get(self.object_name, [])})
        for index in range(1, self.rows + 1):
            context = self._context(index)
            values = self._known_values(context)
            for field in custom_fields:
                if field not in values:
                    values[field] = self._fallback(field, context)
            yield {output: values[field] for output, field in canonical}
