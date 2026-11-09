import pytest


@pytest.fixture
def seeded(client, make_user, make_project):
    """14 projects: μονά -> κατηγορία Web, ζυγά -> CLI."""
    make_user("seeder")
    for i in range(1, 15):
        make_project(title=f"Project {i}", category="Web" if i % 2 else "CLI")
    return 14


def test_home_paginates_at_9(client, seeded):
    assert client.get("/home").text.count('class="project-card"') == 9
    assert client.get("/home?page=2").text.count('class="project-card"') == 5


def test_home_page_out_of_range_is_clamped(client, seeded):
    resp = client.get("/home?page=999")
    assert resp.status_code == 200
    assert "σελίδα 2 από 2" in resp.text


def test_home_category_filter(client, seeded):
    resp = client.get("/home?category=CLI")
    assert "7 projects" in resp.text
    assert 'class="project-card"' in resp.text


def test_home_text_search_on_title(client, seeded):
    # "Project 1" matches 1, 10, 11, 12, 13, 14 -> 6
    resp = client.get("/home?q=Project 1")
    assert "6 projects" in resp.text


def test_home_no_results_message(client, seeded):
    resp = client.get("/home?q=zzz-nothing-matches")
    assert "Δεν βρέθηκαν projects" in resp.text


def test_home_pagination_links_preserve_filters(client, seeded):
    # q=Project matches all 14 -> 2 pages; the next link must carry the filter
    resp = client.get("/home?q=Project")
    assert "/home?q=Project&amp;page=2" in resp.text


def test_home_tech_filter(client, make_user, make_project):
    make_user("t")
    # create a technology through the JSON endpoint, then a project that uses it
    tech_id = client.post("/technologies/", json={"name": "Rust"}).json()["id"]
    pid = client.post(
        "/create-project",
        data={"title": "Rusty", "category": "Web", "description": "", "github_url": "",
              "technology_ids": [tech_id]},
        follow_redirects=False,
    ).headers["location"].split("/")[2]
    make_project(title="NoTech", category="Web")

    resp = client.get(f"/home?tech={tech_id}")
    assert "Rusty" in resp.text
    assert "NoTech" not in resp.text


def test_home_text_search_matches_description(client, make_user, make_project):
    """Η αναζήτηση πρέπει να πιάνει και την περιγραφή, όχι μόνο τον τίτλο."""
    make_user("writer")
    make_project(title="Άσχετος τίτλος", description="χτισμένο με raylib")
    make_project(title="Κάτι άλλο", description="τίποτα σχετικό")

    resp = client.get("/home?q=raylib")
    assert "1 project" in resp.text
    assert "Άσχετος τίτλος" in resp.text


def test_home_text_search_is_case_insensitive(client, make_user, make_project):
    make_user("writer")
    make_project(title="Κάτι", description="Χτισμένο με RayLib")

    assert "1 project" in client.get("/home?q=raylib").text
