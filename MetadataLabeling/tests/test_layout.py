from solar_metadata_tagger.layout import LayoutResolver, PanelFeature


def test_polygon_assignment() -> None:
    feature = PanelFeature(
        feature_id="p1",
        row="A",
        panel="001",
        polygon=((0.0, 0.0), (0.001, 0.0), (0.001, 0.001), (0.0, 0.001), (0.0, 0.0)),
        center=(0.0005, 0.0005),
    )
    resolver = LayoutResolver((feature,))
    assignment = resolver.resolve(latitude=0.0005, longitude=0.0005)
    assert assignment.row == "A"
    assert assignment.panel == "001"
    assert assignment.method == "polygon"
