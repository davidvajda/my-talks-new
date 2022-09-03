from dataclasses import dataclass

@dataclass
class Person:
    id: int
    name: str
    email: str
    role: str

    sid: str = None
    room: str = None

    def __str__(self) -> None:
        return f"[USER] {self.id} / {self.name} / {self.email} / {self.role}"

    def set_sid(self, sid: int) -> None:
        self.sid = sid

    def set_room(self, room_name) -> None:
        self.room = room_name


    def compare_roles(self, person: "Person") -> bool:
        """Takes other person's instance as an agrument and returns True if they're same role"""
        if self.role == person.role:
            return True
        return False
