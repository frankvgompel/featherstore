from .fixtures import make_table, sorted_datetime_index, get_index_name


def test_rename_table(database, connection, store):
    # Arrange
    NEW_TABLE_NAME = "new_table_name"
    df = make_table()
    store.write_table("table_name", df)
    store.rename_table("table_name", to=NEW_TABLE_NAME)
    table = store.select_table(NEW_TABLE_NAME)
    # Act
    table_names = store.list_tables()
    # Assert
    assert table_names == [NEW_TABLE_NAME]


def test_drop_table(database, connection, store):
    # Arrange
    df = make_table()
    store.write_table("table_name", df)
    store.drop_table("table_name")
    # Act
    table_names = store.list_tables()
    # Assert
    assert table_names == []


def test_list_tables_like(database, connection, store):
    # Arrange
    df = make_table(sorted_datetime_index)
    index_name = get_index_name(df)
    TABLE_NAMES = (
        "a_table",
        "AAPL",
        "MSFT",
        "TSLA",
        "AMZN",
        "FB",
        "2019-01-01",
        "saab",
    )
    for table_name in TABLE_NAMES:
        store.write_table(table_name, df, index=index_name)
    # Act
    tables_like_unbounded_wildcard = store.list_tables(like="A%")
    tables_like_bounded_wildcards = store.list_tables(like="?A??")
    # Assert
    assert tables_like_unbounded_wildcard == ["AAPL", "AMZN", "a_table"]
    assert tables_like_bounded_wildcards == ["AAPL", "saab"]


def test_get_columns(database, connection, store):
    # Arrange
    df = make_table(sorted_datetime_index)
    index_name = get_index_name(df)
    expected = df.column_names
    store.write_table("table_name", df, index=index_name)
    table = store.select_table("table_name")
    # Act
    columns = table.columns
    # Assert
    assert columns == expected


def test_get_index(database, connection, store):
    # Arrange
    df = make_table(sorted_datetime_index, astype="pandas")
    index_name = get_index_name(df)
    expected = df.index
    store.write_table("table_name", df, index=index_name)
    table = store.select_table("table_name")
    # Act
    index = table.index
    # Assert
    assert index.equals(expected)
    assert index.name == expected.name
