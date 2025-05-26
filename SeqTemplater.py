#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  9 11:33:18 2025

Sequencer Import File Generator

Modes:
- End Seq: forward + reverse, ID = YYMMDDPCK1 (today)
- Full Seq: forward only, ID = YYMMDDSEQ1 (today)
- HIDI: no input files, ID = YYMMDDHIDI (today)

@author: gkurejsepi
"""

import streamlit as st
import pandas as pd
import datetime
import pytz
from io import StringIO

# Generate the correct sequence ID
def generate_seq_id(suffix):
    tz = pytz.timezone('Asia/Singapore')  # GMT+8
    now = datetime.datetime.now(tz)
    return now.strftime('%y%m%d') + suffix
    # if suffix in ["SEQ1", "HIDI"]:
       # return now.strftime('%y%m%d') + suffix
   # else:
        # Use previous weekday for PCK1
       # one_day = datetime.timedelta(days=1)
       # while True:
         #   now -= one_day
           # if now.weekday() < 5:  # Mon-Fri are 0–4
              #  return now.strftime('%y%m%d') + suffix

# Load the 96-well plate template
@st.cache_data
def load_template():
    return pd.read_csv("3730xlTemplate.txt", sep="\t", dtype=str, keep_default_na=False)

# --- Streamlit UI ---
st.title("Sequencer Import File Generator V1.1")

# Sequencing mode
seq_type = st.radio("Select Sequencing Type", options=["End Seq (PCK)", "Full Seq (SEQ)", "HIDI"])

# File uploads depending on mode
forward_file = None
reverse_file = None

if seq_type in ["End Seq (PCK)", "Full Seq (SEQ)"]:
    forward_file = st.file_uploader("Upload Forward File", type=["tab"])
if seq_type == "End Seq (PCK)":
    reverse_file = st.file_uploader("Upload Reverse File", type=["tab"])

# Main button
generate_button = st.button("Generate Sequencer Import Files")

# Determine if we can proceed
can_run = (
    seq_type == "HIDI" or
    (seq_type == "Full Seq (SEQ)" and forward_file) or
    (seq_type == "End Seq (PCK)" and forward_file and reverse_file)
)

# Run processing
if generate_button and can_run:
    # Load template
    template_df = load_template()
    template_df.fillna('', inplace=True)

    # Only modify wells if required
    if seq_type in ["Full Seq (SEQ)", "End Seq (PCK)"]:
        wells = template_df.iloc[4:, 0].tolist()
        well_map = {
            str(well).strip()[-3:]: idx
            for idx, well in enumerate(wells)
            if pd.notna(well)
        }

        # Process forward input
        forward_file.seek(0)
        forward_lines = pd.read_csv(forward_file, sep="\t", header=None, dtype=str).iloc[:, 0].tolist()
        for string in forward_lines:
            string = str(string).strip()
            code = string[-3:]
            if code in well_map:
                row_idx = well_map[code] + 4  # Offset for header
                template_df.iat[row_idx, 1] = string

        # Process reverse input (End Seq only)
        if seq_type == "End Seq (PCK)":
            reverse_file.seek(0)
            reverse_lines = pd.read_csv(reverse_file, sep="\t", header=None, dtype=str).iloc[:, 0].tolist()
            for string in reverse_lines:
                string = str(string).strip()
                code = string[-3:]
                if code in well_map:
                    row_idx = well_map[code] + 48 + 4  # Offset for reverse + header
                    if row_idx < len(template_df):
                        template_df.iat[row_idx, 1] = string

    # Generate ID
    suffix = {
        "Full Seq (SEQ)": "SEQ1",
        "End Seq (PCK)": "PCK1",
        "HIDI": "HIDI"
    }[seq_type]
    seq_id = generate_seq_id(suffix)

    # Insert ID into A2 and B2 (row=1 in Excel = index 0 in pandas)
    template_df.iat[0, 0] = seq_id
    template_df.iat[0, 1] = seq_id

    # Output to string buffer
    output_buffer = StringIO()
    template_df.to_csv(output_buffer, sep="\t", index=False)
    output_txt = output_buffer.getvalue().encode()

    # Download button
    st.success(f"{seq_type} template generated.")
    st.download_button(
        label="Download Modified Template",
        data=output_txt,
        file_name=f"{seq_id}.txt",
        mime="text/plain"
    )
