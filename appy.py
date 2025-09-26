"""
Author: Dr. Yousra Abdelatti
All Rights Reserved © Dr. Yousra Abdelatti
Smart Homecare Scheduler - Mobile Friendly Edition
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import random

# ---- Staff ----
staff = [
    {"name": "Dr. Ahmed", "role": "Specialist"},
    {"name": "Dr. Sara", "role": "Specialist"},
    {"name": "Dr. Omar", "role": "GP"},
    {"name": "Nurse Fatima", "role": "Nurse"}
]

visit_durations = {"initial": 60, "follow-up": 30, "urgent": 60, "emergency": 90}

WORK_START_MIN = 8*60
WORK_END_MIN = 18*60
SLOT_STEP_MIN = 30

# ---- Helpers ----
def minutes_from_str(tstr):
    h,m=map(int,tstr.split(":"))
    return h*60+m
def str_from_minutes(m):
    return f"{m//60:02d}:{m%60:02d}"
def round_up_to_slot(mins):
    return ((mins+SLOT_STEP_MIN-1)//SLOT_STEP_MIN)*SLOT_STEP_MIN

def assign_staff_candidates(patient, schedule_df):
    candidates = staff.copy()
    if not schedule_df.empty:
        workload = schedule_df['assigned_staff'].value_counts().to_dict()
        candidates.sort(key=lambda s: workload.get(s["name"],0))
    return candidates

def is_available(schedule_df, staff_name, date_iso, start_min, end_min):
    same_staff = schedule_df[(schedule_df['assigned_staff']==staff_name)&(schedule_df['date']==date_iso)]
    for _, row in same_staff.iterrows():
        s = minutes_from_str(row['start_time'])
        e = minutes_from_str(row['end_time'])
        if not (end_min <= s or start_min >= e): return False
    return True

def find_next_available_slot(schedule_df, assigned, day_date, duration):
    latest = WORK_END_MIN-duration
    start = round_up_to_slot(WORK_START_MIN)
    while start <= latest:
        if is_available(schedule_df, assigned["name"], day_date.isoformat(), start, start+duration):
            return start, start+duration
        start += SLOT_STEP_MIN
    return None, None

def next_visit_id(schedule_df):
    if schedule_df.empty: return 1
    nums = pd.to_numeric(schedule_df['visit_id'].str.replace(r"\D","",regex=True), errors='coerce').dropna()
    return int(nums.max())+1 if not nums.empty else 1

def generate_weekly_schedule(patients, start_date=None):
    if start_date is None: start_date=date.today()
    schedule_entries=[]
    schedule_df=pd.DataFrame(schedule_entries)
    for day_offset in range(7):
        day=start_date+timedelta(days=day_offset)
        for patient in patients:
            dur = visit_durations.get(patient.get("visit_type","follow-up"),30)
            for assigned in assign_staff_candidates(patient, schedule_df):
                s,e = find_next_available_slot(schedule_df, assigned, day, dur)
                if s is not None:
                    vid=f"V{next_visit_id(schedule_df):04d}"
                    schedule_entries.append({
                        "visit_id":vid, "date":day.isoformat(), "patient_name":patient["name"],
                        "patient_id":patient["id"], "diagnosis":patient["diagnosis"], "visit_type":patient["visit_type"],
                        "assigned_staff":assigned["name"], "staff_role":assigned["role"],
                        "start_time":str_from_minutes(s), "end_time":str_from_minutes(e)
                    })
                    schedule_df=pd.DataFrame(schedule_entries)
                    break
    return pd.DataFrame(schedule_entries)

# ---- Streamlit UI ----
st.set_page_config(page_title="🏥 Smart Homecare Scheduler", layout="wide")

# Header with color
st.markdown("<h1 style='color:#ff4b4b;'>🏥 Smart Homecare Scheduler</h1>", unsafe_allow_html=True)

if "patients" not in st.session_state: st.session_state.patients=[]
if "schedule" not in st.session_state: st.session_state.schedule=pd.DataFrame()

menu=["Add Patient","View Patients","Generate Schedule","View Schedule","Insert Emergency"]
choice=st.sidebar.selectbox("Menu",menu)

if choice=="Add Patient":
    st.markdown("## ➕ Add Patient", unsafe_allow_html=True)
    with st.form("add_patient"):
        name=st.text_input("Patient Name")
        pid=st.text_input("Patient ID")
        diag=st.text_input("Diagnosis")
        vtype=st.selectbox("Visit Type", ["initial","follow-up","urgent"])
        submitted=st.form_submit_button("Add")
        if submitted:
            st.session_state.patients.append({"name":name,"id":pid,"diagnosis":diag,"visit_type":vtype})
            st.success(f"Added {name}")

elif choice=="View Patients":
    st.markdown("## 🧾 Patient List")
    st.dataframe(pd.DataFrame(st.session_state.patients))

elif choice=="Generate Schedule":
    if not st.session_state.patients:
        st.warning("No patients yet")
    else:
        st.session_state.schedule=generate_weekly_schedule(st.session_state.patients)
        st.success("✅ Schedule Generated")
        st.dataframe(st.session_state.schedule)

elif choice=="View Schedule":
    if st.session_state.schedule.empty:
        st.info("No schedule yet")
    else:
        st.dataframe(st.session_state.schedule)

elif choice=="Insert Emergency":
    st.markdown("## 🚨 Insert Emergency")
    with st.form("emergency"):
        name=st.text_input("Emergency Name")
        pid=st.text_input("ID")
        diag=st.text_input("Diagnosis")
        submitted=st.form_submit_button("Add Emergency")
        if submitted:
            emergency={"name":name,"id":pid,"diagnosis":diag,"visit_type":"emergency"}
            candidates=assign_staff_candidates(emergency, st.session_state.schedule)
            random.shuffle(candidates)
            today=date.today()
            for assigned in candidates:
                s,e=find_next_available_slot(st.session_state.schedule, assigned, today, visit_durations["emergency"])
                if s is not None:
                    vid=f"V{next_visit_id(st.session_state.schedule):04d}"
                    st.session_state.schedule=pd.concat([
                        st.session_state.schedule,pd.DataFrame([{
                            "visit_id":vid,"date":today.isoformat(),"patient_name":name,"patient_id":pid,
                            "diagnosis":diag,"visit_type":"emergency",
                            "assigned_staff":assigned["name"],"staff_role":assigned["role"],
                            "start_time":str_from_minutes(s),"end_time":str_from_minutes(e)
                        }])
                    ], ignore_index=True)
                    st.success(f"Emergency Scheduled with {assigned['name']}")
                    break
