from dataclasses import dataclass

@dataclass
class Person:
    id: int
    name: str
    email: str
    role: str

def __str__(self) -> None:
    return f"[USER] {self.id} / {self.name} / {self.email} / {self.role}"

def set_sid(self, sid: int) -> None:
    self.sid = sid