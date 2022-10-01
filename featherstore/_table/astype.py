import pyarrow as pa

from featherstore.connection import Connection
from featherstore._table import _raise_if
from featherstore._table import _table_utils
from featherstore._table import common
from featherstore._metadata import Metadata


def can_change_type(cols, astype, table_path):
    Connection._raise_if_not_connected()
    _raise_if.table_not_exists(table_path)

    _raise_if.cols_argument_is_not_collection(cols)
    _raise_if.to_is_provided_twice(cols, astype)
    _raise_if.to_not_provided(cols, astype)

    if not isinstance(cols, dict):
        _raise_if.to_argument_is_not_sequence(astype)
        _raise_if.length_of_cols_and_to_doesnt_match(cols, astype)
    cols = common.format_cols_and_to_args(cols, astype)

    _raise_if.cols_argument_items_is_not_str(cols.keys())
    _raise_if_astype_items_is_not_arrow_types(cols.values())

    _raise_if.col_names_contains_duplicates(cols.keys())
    _raise_if.cols_not_in_table(cols.keys(), table_path)
    _raise_if_new_index_type_is_not_valid(cols, table_path)


def _raise_if_astype_items_is_not_arrow_types(astype):
    col_elements_are_arrow_types = all(isinstance(item, pa.DataType) for item in astype)
    if not col_elements_are_arrow_types:
        raise TypeError("Elements in 'to' must be Arrow types")


def _raise_if_new_index_type_is_not_valid(cols, table_path):
    index_name = Metadata(table_path, 'table')['index_name']
    if index_name in cols.keys():
        new_index_dtype = cols[index_name]
        __raise_if_index_is_not_supported_type(new_index_dtype)


def __raise_if_index_is_not_supported_type(dtype):
    is_integer = pa.types.is_integer(dtype)
    is_temporal = pa.types.is_temporal(dtype)
    is_string = pa.types.is_string(dtype) or pa.types.is_large_string(dtype)
    if not is_integer and not is_temporal and not is_string:
        raise TypeError(f"Table.index type must be either int, str or "
                        f"datetime (is type {dtype})")


def change_type(df, cols):
    df = df.combine_chunks()

    schema = df.schema
    for col, dtype in cols.items():
        idx = schema.get_field_index(col)
        field = schema.field(idx)
        field = field.with_type(dtype)
        schema = schema.set(idx, field)
    df = df.cast(schema)
    return df


def create_partitions(df, rows_per_partition, partition_names=None):
    partitions = _table_utils.make_partitions(df, rows_per_partition)
    partition_names = _add_or_remove_partition_ids(partitions, partition_names)
    partitions = _table_utils.assign_ids_to_partitions(partitions, partition_names)
    return partitions


def _add_or_remove_partition_ids(partitions, partition_ids):
    if len(partitions) < len(partition_ids):
        partition_ids = partition_ids[:len(partitions)]
    else:
        partition_ids = _table_utils.add_new_partition_ids(partitions, partition_ids)
    return partition_ids


def get_partitions_to_drop(partitions, stored_names):
    partition_names = partitions.keys()
    partitions_to_drop = set(stored_names) - set(partition_names)
    return sorted(list(partitions_to_drop))
