import pandas as pd
import pysftp
import datetime
import logging
import prefect
import os
import tempfile

from typing import Any, Optional
from prefect import Task
from prefect.utilities.tasks import defaults_from_attrs
from box import Box
import pandera as pa


class PaSchemaFromDatadict(Task):
    """
    Creates Pd Dataframe dictionaries and related Pa DataFrameSchema
    
    Return a Box containing named datadictionary dataframes and pandera dataframeschema
    """

    def __init__(self, datadict: pd.DataFrame = None, **kwargs: Any):
        self.datadict = datadict
        super().__init__(**kwargs)

    def pandera_schema_from_dataframe(self, df: pd.DataFrame) -> pa.DataFrameSchema:
        pa_cols = {}

        for row in df.to_dict(orient="records"):
            pa_cols[row["name"]] = pa.Column(
                name=row["name"],
                pandas_dtype=row["pandas_dtype"],
                nullable=row["nullable"],
                allow_duplicates=row["allow_duplicates"],
                coerce=row["coerce"],
                required=row["required"],
                regex=row["regex"],
                checks=None,
            )

        return pa.DataFrameSchema(pa_cols)

    @defaults_from_attrs("datadict")
    def run(
        self, datadict: pd.DataFrame = None, **format_kwargs: Any
    ) -> pa.DataFrameSchema:
        with prefect.context(**format_kwargs) as data:
            self.logger.info("Creating Pandera schema using datadictionary Dataframe")

            pa_schema = self.pandera_schema_from_dataframe(datadict)

            return pa_schema


class PaSchemaFromFile(Task):
    """
    Creates Pd Dataframe dictionaries and related Pa DataFrameSchema
    
    Return a Box containing named datadictionary dataframes and pandera dataframeschema
    """

    def __init__(self, filepaths: Box = None, **kwargs: Any):
        self.filepaths = filepaths
        super().__init__(**kwargs)

    def pandera_schema_from_dataframe(self, pa_df: pd.DataFrame) -> pa.DataFrameSchema:
        pa_cols = {}

        for row in pa_df.to_dict(orient="records"):
            pa_cols[row["name"]] = pa.Column(
                name=row["name"],
                pandas_dtype=row["pandas_dtype"],
                nullable=row["nullable"],
                allow_duplicates=row["allow_duplicates"],
                coerce=row["coerce"],
                required=row["required"],
                regex=row["regex"],
                checks=None,
            )

        return pa.DataFrameSchema(pa_cols)

    @defaults_from_attrs("filepaths")
    def run(self, filepaths: Box = None, **format_kwargs: Any) -> Box:

        with prefect.context(**format_kwargs) as data:
            return_schema = Box()
            for name, filepath in filepaths.items():
                self.logger.info(
                    "Creating Pandera schema '{}' using datadictionary based on file {}".format(
                        name, filepath
                    )
                )
                return_schema[name] = {"datadict": pd.read_csv(filepath)}
                return_schema[name]["schema"] = self.pandera_schema_from_dataframe(
                    return_schema[name].datadict
                )

            return return_schema


class PaValidate(Task):
    """
    Validates Pandas Dataframes with related Pandera DataFrameSchema. 
    
    Note: assumes Box configuration with names that match between Dataframe and DataFrameSchema
    
    Return a Box containing named pandas DataFrames
    """

    def __init__(
        self,
        df: pd.DataFrame = None,
        schema: pa.DataFrameSchema = None,
        head: Optional[int] = None,
        tail: Optional[int] = None,
        sample: Optional[int] = None,
        random_state: Optional[int] = None,
        **kwargs: Any
    ):
        self.df = df
        self.schema = schema
        self.head = head
        self.tail = tail
        self.sample = sample
        self.random_state = random_state
        super().__init__(**kwargs)

    @defaults_from_attrs(
        "df", "schema", "head", "tail", "sample", "random_state",
    )
    def run(
        self,
        df: pd.DataFrame = None,
        schema: pa.DataFrameSchema = None,
        head: Optional[int] = None,
        tail: Optional[int] = None,
        sample: Optional[int] = None,
        random_state: Optional[int] = None,
        **format_kwargs: Any
    ) -> pd.DataFrame:

        with prefect.context(**format_kwargs) as data:

            self.logger.info("Validating dataframe using Pandera schema")
            df = schema.validate(
                df, head=head, tail=tail, sample=sample, random_state=random_state,
            )

            return df
