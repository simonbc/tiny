def test_landing_page_shows_prompt_textarea(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "<textarea" in body
    assert 'name="prompt"' in body
