from datetime import date
from typing import Optional

import requests

from config import API_KEY
from models import Member

from .database import Database

parse_code = lambda code: code.strip("#")


class WholeClub:
    def __init__(self, main: str, feeders: Optional[list[str]] = None) -> None:
        self.main = main
        self.feeders = feeders

    @property
    def members(self) -> list[Member]:
        return Database().get_members()

    @property
    def trophies(self) -> int:
        return sum(member.trophies for member in self.members)

    @property
    def month_birthdays(self) -> list[Member]:
        real_names_in_current_month = set()
        birthdays = []

        for m in self.members:
            if m.birthday and m.birthday.month == date.today().month:
                if m.real_name not in real_names_in_current_month:
                    birthdays.append(m)
                    real_names_in_current_month.add(m.real_name)

        return birthdays

    @property
    def countries(self) -> dict[str, int]:
        countries = {}
        for m in self.members:
            if m.country not in countries:
                countries[m.country] = 1
            else:
                countries[m.country] += 1
        return dict(sorted(countries.items(), key=lambda item: item[1], reverse=True))

    def __fetch_members(self, code: str) -> list[Member]:
        data = []
        headers = {"Authorization": f"Bearer {API_KEY}"}
        base_url = f"https://bsproxy.royaleapi.dev/v1/clubs"

        code = parse_code(code)
        response = requests.get(f"{base_url}/%23{code}", headers=headers)
        if response.status_code == 200:
            res_json = response.json()

            for member in res_json["members"]:
                member["club"] = res_json
                data.append(Member.from_dict(member))

        return data

    def update_members(self) -> None:
        db = Database()
        current_members = self.__fetch_members(self.main)

        if self.feeders:
            for feeder in self.feeders:
                current_members += self.__fetch_members(feeder)

        saved_members = db.get_members()
        former_members = [m for m in saved_members if m not in current_members]

        for former_member in former_members:
            db.add_former_member(former_member)
            db.remove_member(former_member)

        for member in current_members:
            db.save_member(member)
