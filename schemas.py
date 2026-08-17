from pydantic import BaseModel, EmailStr
from enum import Enum


class TechnologyBase(BaseModel):  # Κλάση Α
    name : str
    

class TechnologyCreate(TechnologyBase):
    pass     #Δεν προσθέτει τίποτα νέο, απλά χρησιμοποιείται για να ξεχωρίζουμε τα schemas που χρησιμοποιούνται για δημιουργία.

class Technology(TechnologyBase):
    id : int # Id του αντικειμένου που επιστρέφεται από την βάση δεδομένων.

    class Config:
        orm_mode = True

class UserBase(BaseModel): #Κλάση Β
    username: str
    email: EmailStr  #Validation σε περιπτωση που το email δεν είναι έγκυρο.

class UserCreate(UserBase):
    password: str 
    # Προσθέτουμε το πεδίο password για τη δημιουργία χρήστη. 
    # Είναι σε διαφορετική κλάση για λόγους ασφαλείας.


class User(UserBase):
    id: int

    class Config:
        from_attributes = True  # Επιτρέπει την μετατροπή από SQLAlchemy μοντέλα σε Pydantic μοντέλα.

class ProjectBase(BaseModel): #Κλάση Γ
    title: str
    description: str | None = None #Προαιρετικό πεδίο, μπορεί να είναι None.
    category: str
    github_url: str | None = None #Το ίδιο με το description.

class ProjectCreate(ProjectBase):
    technology_ids: list[int] = []  # Λίστα με τα IDs των τεχνολογιών που σχετίζονται με το project.


class Project(ProjectBase):
    id: int
    owner: User
    technologies: list[Technology] = []  # Λίστα με τα αντικείμενα Technology που σχετίζονται με το project.

    class Config:
        from_attributes = True  # Επιτρέπει την μετατροπή από SQLAlchemy μοντέλα σε Pydantic μοντέλα.



#-----------------------------------------------------------------------------------

#Version , Comment, Rating schemas

class Version(BaseModel):
    id: int
    version_number: str
    changelog: str | None = None

    class Config:
        from_attributes = True

class VersionCreate(BaseModel):
    version_number: str
    changelog: str | None = None

class CommentCategory(str, Enum):
    feature_idea = "Feature Idea"
    bug_report = "Bug Report"

class CommentBase(BaseModel):
    content: str
    category: CommentCategory

class CommentCreate(CommentBase):
    pass

class Comment(CommentBase):
    id: int
    user: User

    class Config:
        from_attributes = True

class RatingBase(BaseModel):
    stars: int

class RatingCreate(RatingBase):
    pass

class Rating(RatingBase):
    id: int
    user: User

    class Config:
        from_attributes = True
    


