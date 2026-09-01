from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Table, UniqueConstraint  # ΑΛΛΑΓΗ: πρόσθεσα UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


# Opinion: Σχέση πολλών προς πολλά μεταξύ Project και Technology
# Ο κώδικας είναι το SQL μας προκειμένουν να αποθηκεύσουμε τις τεχνολογίες--
# --που χρησιμοποιούνται σε κάθε project. 
# Χρησιμοποιούμε ένα association table (project_technologies) για να συνδέσουμε τα δύο μοντέλα.
# Στο μέλλον μπορούμε να αντικαταστήσουμε το SQLAlchemy με άλλο μοντέλο. 

project_technologies = Table(
    "project_technologies",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id"), primary_key=True),
    Column("technology_id", Integer, ForeignKey("technologies.id"), primary_key=True),
)


class Technology(Base):
    __tablename__ = "technologies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)

    projects = relationship("Project", secondary=project_technologies, back_populates="technologies")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    bio = Column(String, nullable=True)
    projects = relationship("Project", back_populates="owner")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False)  # ΑΛΛΑΓΗ: πρόσθεσα το πεδίο που έλειπε
    github_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    image_url = Column(String, nullable=True)
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="projects")
    versions = relationship("Version", back_populates="project", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="project", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="project", cascade="all, delete-orphan")
    technologies = relationship("Technology", secondary=project_technologies, back_populates="projects")  # ΑΛΛΑΓΗ: αντικατέστησε το tech_stack



class Version(Base):
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, index=True)
    version_number = Column(String, nullable=False)
    changelog = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="versions")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=False)  # ΑΛΛΑΓΗ: πρόσθεσα το πεδίο που έλειπε ("feature_idea" / "bug_report")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    project = relationship("Project", back_populates="comments")
    user = relationship("User")


class Rating(Base):  
    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint('user_id', 'project_id', name='unique_user_project_rating'),)

    id = Column(Integer, primary_key=True, index=True)
    stars = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    project = relationship("Project", back_populates="ratings")
    user = relationship("User")