from datetime import datetime, date
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin

class Announcement(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'announcements'

    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    target_audience = db.Column(db.String(50), default='All', nullable=False) # All, Department, Role
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    publish_date = db.Column(db.Date, default=date.today, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)

    department = db.relationship('Department', foreign_keys=[department_id])

    def __repr__(self):
        return f"<Announcement {self.title}>"


class Notification(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'notifications'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    notification_type = db.Column(db.String(50), default='Info', nullable=False) # Info, Success, Warning, Danger

    user = db.relationship('User', backref='notifications', foreign_keys=[user_id])

    def __repr__(self):
        return f"<Notification {self.title} to User {self.user_id}>"


class Message(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'messages'

    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    parent_message_id = db.Column(db.Integer, db.ForeignKey('messages.id', ondelete='SET NULL'), nullable=True)
    is_broadcast = db.Column(db.Boolean, default=False, nullable=False)
    attachment_path = db.Column(db.String(255), nullable=True)

    sender = db.relationship('User', foreign_keys=[sender_id])
    recipients = db.relationship('MessageRecipient', back_populates='message', cascade='all, delete-orphan')
    replies = db.relationship('Message', backref=db.backref('parent_message', remote_side='Message.id'))

    def __repr__(self):
        return f"<Message {self.subject}>"


class MessageRecipient(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'message_recipients'

    message_id = db.Column(db.Integer, db.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    is_starred = db.Column(db.Boolean, default=False, nullable=False)

    message = db.relationship('Message', back_populates='recipients')
    recipient = db.relationship('User', foreign_keys=[recipient_id])
