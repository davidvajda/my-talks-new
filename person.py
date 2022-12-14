from dataclasses import dataclass

@dataclass
class Person:
    id: int
    name: str
    email: str
    role: str

    image: str = None
    sid: str = None
    room: str = None
    paired_person_sid: int = None

    def __str__(self) -> None:
        return f"ID: {self.id}  \nNAME: {self.name} \nMAIL: {self.email} \nROLE: {self.role} \nSID: {self.sid} \nROOM: {self.room} \nPAIRED PERSON {self.paired_person_id}\n"

    def jsonify(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "sid": self.sid,
            "room": self.room,
        }

    def set_sid(self, sid: int) -> None:
        self.sid = sid

    def set_room(self, room_name) -> None:
        self.room = room_name

    def compare_roles(self, person: "Person") -> bool:
        """Takes other person's instance as an agrument and returns True if they're same role"""
        if self.role == person.role:
            return True
        return False

    def pair_person(self, person_sid) -> None:
        self.paired_person_id = person_sid

    def unpair(self) -> None:
        self.paired_person_id = None

