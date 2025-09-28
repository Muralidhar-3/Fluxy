from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(200), index=True)  # Symbol like "RELIANCE"
    companyName = db.Column(db.String(500))  # Full company name like "Reliance Industries Limited"
    title = db.Column(db.String(500))  # Announcement title/description
    desc = db.Column(db.Text, nullable=True)  # Additional description from attchmntText
    date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    link = db.Column(db.String(500), nullable=True)  # Link to attachment file

    def to_dict(self):
        return {
            "id": self.id,
            "company": self.company,
            "companyName": self.companyName,
            "title": self.title,
            "desc": self.desc,
            "date": self.date.strftime("%Y-%m-%d %H:%M"),
            "link": self.link,
        }