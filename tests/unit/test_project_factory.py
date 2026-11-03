from scripts._project_factory.local import values


def test_existing_project_without_openssf_registration_has_no_badge_url():
    rendered = values(
        profile="ansible",
        owner="kpeacocke",
        name="ansible-collection-draytek",
        description="",
        source_repository="kpeacocke/engineering-baseline-template",
        openssf_project="",
    )

    assert rendered["OPENSSF_PROJECT"] == ""
    assert rendered["OPENSSF_PROJECT_ID"] == ""
