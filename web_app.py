#!/usr/bin/env python3
"""
量化交易策略管理 Web 应用

基于 run_iterative_optimization.py 和 strategy_scanner.py 的核心功能
提供可读、可写、可选、可看的完整界面

运行方式:
streamlit run web_app.py
"""

import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import time
import subprocess
import sys
import threading
import queue
from io import StringIO
import plotly.graph_objects as go
import plotly.express as px
from backtest_engine import OptionBacktest
from monitor_cache import MonitorCache

# 页面配置
st.set_page_config(
    page_title="量化交易策略管理平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"  # Show sidebar for navigation
)

# 自定义 CSS - Updated to match RockAlpha design with top navigation
st.markdown("""
<style>
    /* RockAlpha-inspired light theme with white background */
    html, body {
        background: #FFFFFF !important;
        background-image: none !important;
        color: #1F2937;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        min-height: 100vh;
    }
    
    /* Override Streamlit default background */
    #root {
        background: #FFFFFF !important;
    }
    
    /* Ensure all Streamlit containers use white background */
    [data-testid="stAppViewContainer"] {
        background: #FFFFFF !important;
    }
    
    [data-testid="stAppViewContainer"] > div {
        background: #FFFFFF !important;
    }
    
    /* Streamlit main container */
    .main {
        background: #FFFFFF !important;
    }
    
    /* Block container - optimized layout */
    .main .block-container {
        background: #FFFFFF !important;
        padding-top: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
        margin-left: 0 !important;
    }
    
    /* Reduce main content left margin when sidebar is visible */
    .main > div:first-child {
        margin-left: 0 !important;
    }
    
    /* Adjust main content area to use more space */
    [data-testid="stAppViewContainer"] > div:first-child {
        padding-left: 0 !important;
    }
    
    /* Reduce spacing between sidebar and main content */
    [data-testid="stAppViewContainer"] {
        gap: 0 !important;
    }
    
    /* Adjust top padding since Streamlit header is hidden */
    #MainMenu {
        visibility: hidden;
    }
    
    /* Hide Streamlit footer */
    footer[data-testid='stFooter'] {
        display: none !important;
    }
    
    .nav-title {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #A855F7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        letter-spacing: -0.02em;
    }
    
    .nav-links {
        display: flex;
        gap: 1.5rem;
    }
    
    .nav-link {
        color: #B0B0C0 !important;
        text-decoration: none !important;
        font-weight: 500;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        transition: all 0.3s ease;
        font-size: 1rem;
        border: none !important;
        border-bottom: none !important;
        outline: none !important;
        background: transparent !important;
        cursor: pointer !important;
        font-family: inherit !important;
    }
    
    .nav-link:hover {
        color: #FFFFFF !important;
        background: rgba(161, 0, 255, 0.1) !important;
        text-decoration: none !important;
        border-bottom: none !important;
    }
    
    .nav-link.active {
        color: #FFFFFF !important;
        background: linear-gradient(135deg, #A100FF 0%, #632BFF 100%) !important;
        text-decoration: none !important;
        border-bottom: none !important;
    }
    
    /* Remove any underline from nav links */
    .nav-link:visited,
    .nav-link:active,
    .nav-link:focus {
        text-decoration: none !important;
        border-bottom: none !important;
        outline: none !important;
    }
    
    /* Main header with RockAlpha gradient */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #A855F7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 2rem 0;
        text-align: center;
        letter-spacing: -0.02em;
    }
    
    /* Update text colors for light theme */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: #1F2937 !important;
    }
    
    /* Streamlit text elements */
    [data-testid='stMarkdownContainer'] {
        color: #1F2937 !important;
    }
    
    [data-testid='stText'] {
        color: #1F2937 !important;
    }
    
    /* Ensure Streamlit widgets have white background */
    [data-baseweb="base-input"] {
        background: #FFFFFF !important;
    }
    
    [data-baseweb="select"] > div {
        background: #FFFFFF !important;
    }
    
    /* Selectbox styling */
    [data-baseweb="select"] {
        background: #FFFFFF !important;
        border-color: rgba(0, 0, 0, 0.2) !important;
    }
    
    [data-baseweb="select"] > div {
        background: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-baseweb="popover"] {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
    }
    
    [data-baseweb="popover"] li {
        background: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-baseweb="popover"] li:hover {
        background: #F9FAFB !important;
    }
    
    /* Multiselect styling */
    [data-baseweb="tag"] {
        background: #F3F4F6 !important;
        color: #1F2937 !important;
        border-color: rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Checkbox styling */
    [data-baseweb="checkbox"] {
        background: #FFFFFF !important;
        border-color: rgba(0, 0, 0, 0.3) !important;
    }
    
    [data-baseweb="checkbox"]:checked {
        background: #6366F1 !important;
        border-color: #6366F1 !important;
    }
    
    /* Radio button styling */
    [data-baseweb="radio"] {
        background: #FFFFFF !important;
    }
    
    [data-baseweb="radio"] label {
        color: #1F2937 !important;
    }
    
    /* Radio group container */
    [role="radiogroup"] {
        background: #FFFFFF !important;
    }
    
    [role="radiogroup"] > div {
        background: #FFFFFF !important;
    }
    
    /* Radio button circle indicators */
    [data-baseweb="radio"] > div {
        background: #FFFFFF !important;
        border-color: rgba(99, 102, 241, 0.3) !important;
    }
    
    [data-baseweb="radio"] input:checked + div {
        background: #FFFFFF !important;
        border-color: #6366F1 !important;
    }
    
    /* Radio button inner circle (selected indicator) - change from black to purple */
    [data-baseweb="radio"] input:checked + div::after {
        background: #6366F1 !important;
        background-color: #6366F1 !important;
    }
    
    /* Unselected radio button inner circle - make it light gray instead of black */
    [data-baseweb="radio"] input:not(:checked) + div::after {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* Sidebar radio buttons - more specific styling */
    [data-testid="stSidebar"] [data-baseweb="radio"] > div {
        border-color: rgba(99, 102, 241, 0.3) !important;
    }
    
    [data-testid="stSidebar"] [data-baseweb="radio"] input:checked + div {
        border-color: #6366F1 !important;
    }
    
    [data-testid="stSidebar"] [data-baseweb="radio"] input:checked + div::after {
        background: #6366F1 !important;
        background-color: #6366F1 !important;
    }
    
    /* Ensure all radio button indicators use purple theme */
    [data-baseweb="radio"] input[type="radio"]:checked + div::before,
    [data-baseweb="radio"] input[type="radio"]:checked + div::after {
        background: #6366F1 !important;
        background-color: #6366F1 !important;
    }
    
    /* Override any black/dark colors in radio buttons - use more compatible selectors */
    [data-baseweb="radio"] input[type="radio"]:checked + div[style*="background"] {
        background: #6366F1 !important;
        background-color: #6366F1 !important;
    }
    
    /* Force purple color for all radio button inner circles */
    [data-baseweb="radio"] > div > div,
    [data-baseweb="radio"] > div > div::after,
    [data-baseweb="radio"] > div > div::before {
        background-color: transparent !important;
    }
    
    [data-baseweb="radio"] input:checked ~ div > div,
    [data-baseweb="radio"] input:checked + div > div,
    [data-baseweb="radio"] input:checked + div::after {
        background: #6366F1 !important;
        background-color: #6366F1 !important;
    }
    
    /* Sidebar specific - ensure purple indicators */
    section[data-testid="stSidebar"] [data-baseweb="radio"] input:checked + div::after,
    section[data-testid="stSidebar"] [data-baseweb="radio"] input:checked + div::before {
        background: #6366F1 !important;
        background-color: #6366F1 !important;
    }
    
    /* Slider styling */
    [data-baseweb="slider"] {
        background: #FFFFFF !important;
    }
    
    [data-baseweb="slider"] [role="slider"] {
        background: #6366F1 !important;
        border-color: #6366F1 !important;
    }
    
    [data-baseweb="slider"] [role="slider"]:hover {
        background: #7C3AED !important;
    }
    
    /* Date input styling - match white theme */
    [data-baseweb="datepicker"] {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.2) !important;
        border-radius: 8px !important;
        color: #1F2937 !important;
    }
    
    [data-baseweb="datepicker"] input {
        background: #FFFFFF !important;
        color: #1F2937 !important;
        border: none !important;
    }
    
    [data-baseweb="datepicker"] input::placeholder {
        color: #9CA3AF !important;
    }
    
    [data-baseweb="calendar"] {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Calendar root container - 强制白色 */
    [data-baseweb="calendar"] > div {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    /* 所有日历子元素 - 强制白色或透明 */
    [data-baseweb="calendar"] div,
    [data-baseweb="calendar"] > div > div,
    [data-baseweb="calendar"] div div,
    [data-baseweb="calendar"] span,
    [data-baseweb="calendar"] > * {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    /* 确保没有任何元素使用黑色背景 */
    [data-baseweb="calendar"] *,
    [data-baseweb="calendar"] *::before,
    [data-baseweb="calendar"] *::after {
        background: transparent !important;
        background-color: transparent !important;
        background-image: none !important;
    }
    
    /* 但保持主容器白色 */
    [data-baseweb="calendar"],
    [data-baseweb="calendar"] > div {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    [data-baseweb="calendar"] [role="presentation"] {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    /* 日历网格布局元素 */
    [data-baseweb="calendar"] [class*="Grid"],
    [data-baseweb="calendar"] [class*="grid"] {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    /* Calendar header area */
    [data-baseweb="calendar-header"] {
        background: #FFFFFF !important;
    }
    
    [data-baseweb="calendar-header"] * {
        background: transparent !important;
        color: #1F2937 !important;
    }
    
    /* Calendar month container */
    [data-baseweb="month-container"] {
        background: #FFFFFF !important;
    }
    
    /* Calendar week days header */
    [data-baseweb="week"] {
        background: #FFFFFF !important;
    }
    
    /* Calendar day cells and containers */
    [data-baseweb="calendar"] [role="row"] {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    [data-baseweb="calendar"] [role="gridcell"] {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    [data-baseweb="calendar"] [role="gridcell"] > div {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    [data-baseweb="calendar"] [role="gridcell"] * {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* Calendar buttons - day numbers */
    [data-baseweb="calendar"] button {
        color: #1F2937 !important;
        background: transparent !important;
        background-color: transparent !important;
    }
    
    [data-baseweb="calendar"] button * {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    [data-baseweb="calendar"] button:hover {
        background: #F3F4F6 !important;
        background-color: #F3F4F6 !important;
    }
    
    [data-baseweb="calendar"] button[aria-selected="true"] {
        background: #6366F1 !important;
        background-color: #6366F1 !important;
        color: #FFFFFF !important;
    }
    
    [data-baseweb="calendar"] button[aria-label*="selected"] {
        background: #6366F1 !important;
        background-color: #6366F1 !important;
        color: #FFFFFF !important;
    }
    
    /* 禁用按钮和无效日期 */
    [data-baseweb="calendar"] button:disabled,
    [data-baseweb="calendar"] button[aria-disabled="true"] {
        background: transparent !important;
        background-color: transparent !important;
        opacity: 0.4 !important;
    }
    
    /* Calendar navigation buttons (prev/next month) */
    [data-baseweb="calendar-header"] button {
        background: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-baseweb="calendar-header"] button:hover {
        background: #F3F4F6 !important;
    }
    
    /* FINAL OVERRIDE - 彻底清除任何深色/黑色背景 */
    [data-baseweb="calendar"],
    [data-baseweb="calendar"] *,
    [data-baseweb="calendar"]::before,
    [data-baseweb="calendar"]::after,
    [data-baseweb="calendar"] *::before,
    [data-baseweb="calendar"] *::after {
        background-image: none !important;
        box-shadow: none !important;
    }
    
    /* 确保主容器和关键元素是白色 */
    [data-baseweb="calendar"],
    [data-baseweb="calendar"] > div,
    [data-baseweb="calendar-header"],
    [data-baseweb="month-container"],
    [data-baseweb="week"],
    [data-baseweb="calendar"] [role="row"],
    [data-baseweb="calendar"] [role="gridcell"] {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    /* 所有其他元素透明 */
    [data-baseweb="calendar"] button,
    [data-baseweb="calendar"] span,
    [data-baseweb="calendar"] div div {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* 选中的日期和按钮例外 */
    [data-baseweb="calendar"] button[aria-selected="true"],
    [data-baseweb="calendar"] button[aria-selected="true"] * {
        background: #6366F1 !important;
        background-color: #6366F1 !important;
    }
    
    
    /* File uploader styling */
    [data-testid='stFileUploader'] {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        border-radius: 10px !important;
    }
    
    [data-testid='stFileUploader'] > div {
        background: #FFFFFF !important;
    }
    
    [data-testid='stFileUploader'] section {
        background: #FFFFFF !important;
        border-color: rgba(0, 0, 0, 0.2) !important;
    }
    
    [data-testid='stFileUploader'] * {
        background: transparent !important;
    }
    
    [data-testid='stFileUploader'] button {
        background: #FFFFFF !important;
        color: #1F2937 !important;
        border-color: rgba(0, 0, 0, 0.2) !important;
    }
    
    /* Text area styling */
    textarea {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.2) !important;
        color: #1F2937 !important;
    }
    
    /* Number input styling */
    [data-baseweb="input"] {
        background: #FFFFFF !important;
        border-color: rgba(0, 0, 0, 0.2) !important;
        color: #1F2937 !important;
    }
    
    /* Tabs styling */
    [data-baseweb="tabs"] {
        background: #FFFFFF !important;
    }
    
    [data-baseweb="tab"] {
        color: #6B7280 !important;
        background: #FFFFFF !important;
    }
    
    [data-baseweb="tab"]:hover {
        background: #F9FAFB !important;
        color: #1F2937 !important;
    }
    
    [data-baseweb="tab"][aria-selected="true"] {
        color: #6366F1 !important;
        background: #FFFFFF !important;
    }
    
    /* Progress bar styling */
    [data-baseweb="progress-bar"] {
        background: #F3F4F6 !important;
    }
    
    [data-baseweb="progress-bar"] > div {
        background: #6366F1 !important;
    }
    
    /* Spinner styling */
    [data-testid='stSpinner'] {
        color: #6366F1 !important;
    }
    
    /* Caption styling */
    [data-testid='stCaption'] {
        color: #6B7280 !important;
    }
    
    /* Info/Warning/Success/Error boxes */
    [data-baseweb="notification"] {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        color: #1F2937 !important;
    }
    
    /* Code block styling - white background for logs */
    [data-testid='stCodeBlock'] {
        background: #FFFFFF !important;
        border: none !important;
    }
    
    /* Override pre tag background inside code blocks */
    [data-testid='stCodeBlock'] pre {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
        border: none !important;
    }
    
    [data-testid='stCodeBlock'] code {
        background: transparent !important;
        background-color: transparent !important;
        color: #1F2937 !important;
    }
    
    /* Override any dark theme styles for code blocks */
    pre {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    pre code {
        background: transparent !important;
        background-color: transparent !important;
        color: #1F2937 !important;
    }
    
    /* Metric cards with modern light theme */
    .metric-card {
        background: #FFFFFF;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
        border: 1px solid rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        border-color: rgba(99, 102, 241, 0.3);
        box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.1), 0 2px 4px -1px rgba(99, 102, 241, 0.06);
        transform: translateY(-2px);
    }
    
    /* Success messages */
    .success-box {
        background: linear-gradient(135deg, #0f3b39 0%, #1a5e5a 100%);
        border-left: 4px solid #38ef7d;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: #38ef7d;
    }
    
    /* Warning messages */
    .warning-box {
        background: linear-gradient(135deg, #3b361f 0%, #5e551a 100%);
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: #ffc107;
    }
    
    /* Error messages */
    .error-box {
        background: linear-gradient(135deg, #3b1f24 0%, #5e2a35 100%);
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: #dc3545;
    }
    
    /* Hide Streamlit default header and deploy button */
    header[data-testid='stHeader'] {
        display: none !important;
    }
    
    /* Hide deploy button */
    .stDeployButton {
        display: none !important;
    }
    
    /* Hide Streamlit menu button */
    button[data-testid='baseButton-header'] {
        display: none !important;
    }
    
    /* Hide Streamlit toolbar */
    [data-testid='stToolbar'] {
        display: none !important;
    }
    
    /* Hide Streamlit header actions */
    [data-testid='stHeader'] > div {
        display: none !important;
    }
    
    /* Sidebar styling - white background, but allow collapse/expand */
    section[data-testid='stSidebar'],
    [data-testid='stSidebar'],
    div[data-testid='stSidebar'],
    aside[data-testid='stSidebar'],
    [class*="css-"] section[data-testid='stSidebar'] {
        background: #FFFFFF !important;
        /* Remove forced display/visibility to allow collapse */
        /* display: block !important; */
        /* visibility: visible !important; */
        /* Allow Streamlit to control width for collapse */
        /* width: 16rem !important; */
        /* min-width: 16rem !important; */
        /* max-width: 16rem !important; */
        position: relative !important;
        z-index: 100 !important;
        /* Remove forced transform to allow collapse animation */
        /* transform: translateX(0) !important; */
        /* opacity: 1 !important; */
    }
    
    /* When sidebar is expanded, set width */
    section[data-testid='stSidebar']:not([aria-hidden="true"]) {
        width: 16rem !important;
        min-width: 16rem !important;
        max-width: 16rem !important;
    }
    
    [data-testid='stSidebar'] > div,
    [data-testid='stSidebar'] > section,
    [data-testid='stSidebar'] > div:first-child {
        background: #FFFFFF !important;
        /* Allow Streamlit to control display */
        /* display: block !important; */
        /* visibility: visible !important; */
        width: 100% !important;
    }
    
    [data-testid='stSidebar'] * {
        color: #1F2937 !important;
    }
    
    /* Remove override rules that prevent collapse - allow Streamlit to control */
    /* These rules were preventing the collapse button from working */
    
    /* Ensure collapse button is clickable and functional */
    button[aria-label*="Close"],
    button[aria-label*="Open"],
    button[title*="Close"],
    button[title*="Open"] {
        pointer-events: auto !important;
        cursor: pointer !important;
        z-index: 999 !important;
    }
    
    /* Ensure sidebar collapse button works */
    [data-testid="stSidebar"] ~ button,
    button[aria-label*="sidebar"],
    button[title*="sidebar"] {
        pointer-events: auto !important;
        cursor: pointer !important;
        z-index: 999 !important;
    }
    
    /* Main content area - already defined above */
    
    /* Dataframe styling - Modern light theme - COMPREHENSIVE */
    [data-testid='stDataFrame'] {
        background: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        overflow: visible !important;
        min-height: 100px !important;
    }
    
    [data-testid='stDataFrame'] > div {
        background: #FFFFFF !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    
    [data-testid='stDataFrame'] * {
        opacity: 1 !important;
        visibility: visible !important;
    }
    
    /* Table styling - ensure white background for all tables */
    table {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    thead {
        background: rgba(99, 102, 241, 0.08) !important;
        background-color: rgba(99, 102, 241, 0.08) !important;
    }
    
    tbody {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    th {
        color: #1F2937 !important;
        font-weight: 600 !important;
        border-color: rgba(0, 0, 0, 0.1) !important;
        background: rgba(99, 102, 241, 0.08) !important;
        background-color: rgba(99, 102, 241, 0.08) !important;
    }
    
    td {
        color: #374151 !important;
        border-color: rgba(0, 0, 0, 0.05) !important;
        background: transparent !important;
        background-color: transparent !important;
    }
    
    tr {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    tr:hover {
        background: rgba(99, 102, 241, 0.05) !important;
        background-color: rgba(99, 102, 241, 0.05) !important;
    }
    
    tr:nth-child(even) {
        background: #F9FAFB !important;
        background-color: #F9FAFB !important;
    }
    
    /* Buttons - Modern RockAlpha style */
    button {
        background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%) !important;
        border: none !important;
        color: white !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.5rem 1rem !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
        box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.3), 0 2px 4px -1px rgba(99, 102, 241, 0.2) !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
        white-space: nowrap !important;
        text-overflow: ellipsis !important;
        overflow: hidden !important;
        min-height: 2.25rem !important;
        line-height: 1.2 !important;
    }
    
    button:hover {
        background: linear-gradient(135deg, #7C3AED 0%, #A855F7 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4), 0 4px 6px -2px rgba(99, 102, 241, 0.3) !important;
    }
    
    button:active {
        transform: translateY(0) !important;
    }
    
    /* Secondary button style */
    button[kind="secondary"] {
        background: #F9FAFB !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        color: #1F2937 !important;
        box-shadow: none !important;
    }
    
    button[kind="secondary"]:hover {
        background: #F3F4F6 !important;
        border-color: rgba(99, 102, 241, 0.3) !important;
    }
    
    /* Plotly toolbar buttons - match white theme */
    .modebar {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
    }
    
    .modebar-group {
        background: #FFFFFF !important;
    }
    
    .modebar-btn {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        color: #1F2937 !important;
        border-radius: 4px !important;
    }
    
    .modebar-btn:hover {
        background: #F3F4F6 !important;
        border-color: rgba(99, 102, 241, 0.3) !important;
        color: #6366F1 !important;
    }
    
    .modebar-btn:active {
        background: #E5E7EB !important;
    }
    
    .modebar-btn svg {
        fill: #1F2937 !important;
    }
    
    .modebar-btn:hover svg {
        fill: #6366F1 !important;
    }
    
    /* Plotly modebar container */
    .js-plotly-plot .plotly .modebar {
        background: #FFFFFF !important;
    }
    
    /* Plotly modebar buttons container */
    .js-plotly-plot .plotly .modebar-container {
        background: #FFFFFF !important;
    }
    
    /* Plotly modebar button icons */
    .js-plotly-plot .plotly .modebar-btn path {
        fill: #1F2937 !important;
    }
    
    .js-plotly-plot .plotly .modebar-btn:hover path {
        fill: #6366F1 !important;
    }
    
    /* More specific selectors for Plotly toolbar */
    div[class*="modebar"],
    div[class*="modebar"] > div,
    div[class*="modebar"] button {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    div[class*="modebar"] button {
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        color: #1F2937 !important;
    }
    
    div[class*="modebar"] button:hover {
        background: #F3F4F6 !important;
        background-color: #F3F4F6 !important;
        border-color: rgba(99, 102, 241, 0.3) !important;
    }
    
    div[class*="modebar"] button svg,
    div[class*="modebar"] button path {
        fill: #1F2937 !important;
        stroke: #1F2937 !important;
    }
    
    div[class*="modebar"] button:hover svg,
    div[class*="modebar"] button:hover path {
        fill: #6366F1 !important;
        stroke: #6366F1 !important;
    }
    
    /* Plotly toolbar container background */
    .plotly .modebar-container {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    /* Plotly toolbar group background */
    .plotly .modebar-group {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    /* Stop/Delete button specific styling - use key selector */
    button[key*="stop"], button[key*="del"] {
        min-width: 75px !important;
        max-width: 100px !important;
        font-size: 0.875rem !important;
        padding: 0.5rem 0.8rem !important;
        letter-spacing: 0.01em !important;
        text-align: center !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    /* Ensure button text doesn't wrap or distort */
    button[key*="stop"] > div,
    button[key*="del"] > div,
    button[key*="stop"] span,
    button[key*="del"] span {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        width: 100% !important;
        text-align: center !important;
    }
    
    /* Input fields - Modern light style */
    input, select, textarea {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.2) !important;
        border-radius: 10px !important;
        color: #1F2937 !important;
        padding: 0.625rem 0.875rem !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
        transition: all 0.2s ease !important;
    }
    
    input:focus, select:focus, textarea:focus {
        border: 1px solid #6366F1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
        background: #FFFFFF !important;
        outline: none !important;
    }
    
    input::placeholder, textarea::placeholder {
        color: rgba(107, 114, 128, 0.6) !important;
    }
    
    /* Metrics - Modern style */
    [data-testid='stMetricValue'] {
        color: #6366F1 !important;
        font-weight: 700 !important;
        font-size: 1.5rem !important;
    }
    
    [data-testid='stMetricDelta'] {
        color: #10B981 !important;
        font-weight: 600 !important;
    }
    
    [data-testid='stMetricDelta'][aria-label*="negative"] {
        color: #EF4444 !important;
    }
    
    /* Expander - Modern light style */
    [data-testid='stExpander'] {
        background: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        margin: 1rem 0 !important;
    }
    
    /* Expander header - white background instead of dark */
    [data-testid='stExpander'] > div:first-child {
        background: #FFFFFF !important;
        border-radius: 12px 12px 0 0 !important;
        padding: 1rem !important;
        border-bottom: none !important;
    }
    
    [data-testid='stExpander'] summary {
        color: #1F2937 !important;
        font-weight: 600 !important;
        background: transparent !important;
    }
    
    /* Override any dark background in expander header */
    [data-testid='stExpander'] > div:first-child > div {
        background: transparent !important;
    }
    
    /* Expander header text */
    [data-testid='stExpander'] summary,
    [data-testid='stExpander'] > div:first-child * {
        color: #1F2937 !important;
    }
    
    /* Override Streamlit expander header dark background */
    [data-testid='stExpander'] > div:first-child {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* Status badge styling - replace green with purple/blue for white theme */
    /* Target status text in expander headers and content */
    [data-testid='stExpander'] summary,
    [data-testid='stExpander'] * {
        /* Override any green color for RUNNING status */
    }
    
    /* Status badges in markdown - replace green with theme color */
    code {
        background: #F3F4F6 !important;
        color: #1F2937 !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Status text styling - make RUNNING status use theme color instead of green */
    /* This will target status text in expander titles and content */
    
    /* Footer */
    footer {
        background: #FFFFFF !important;
        padding: 1.5rem;
        border-top: 1px solid rgba(0, 0, 0, 0.1);
        margin-top: 2rem;
        text-align: center;
        color: rgba(107, 114, 128, 0.8) !important;
    }
    
    /* Info/Warning/Success boxes */
    .stAlert {
        border-radius: 12px !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Selectbox and other widgets */
    [data-baseweb="select"] {
        background: #FFFFFF !important;
        border-color: rgba(0, 0, 0, 0.2) !important;
    }
    
    /* Checkbox */
    [data-baseweb="checkbox"] {
        border-color: rgba(0, 0, 0, 0.3) !important;
    }
    
    [data-baseweb="checkbox"]:checked {
        background: #6366F1 !important;
        border-color: #6366F1 !important;
    }
    
    /* Reduce spacing in expanders and containers */
    [data-testid='stExpander'] > div {
        padding: 0.5rem 1rem !important;
    }
    
    /* Reduce spacing between markdown elements */
    .main .block-container .element-container {
        margin-bottom: 0.2rem !important;
    }
    
    /* Compact markdown spacing */
    .main .block-container p {
        margin: 0.15rem 0 !important;
        line-height: 1.4 !important;
    }
    
    /* Compact columns spacing */
    [data-testid='column'] {
        padding: 0.25rem !important;
    }
    
    /* Ensure no overflow in expanders */
    [data-testid='stExpander'] {
        max-width: 100% !important;
        overflow: hidden !important;
        border: none !important;
    }
    
    [data-testid='stExpander'] > div {
        max-width: 100% !important;
        overflow-x: auto !important;
        border: none !important;
    }
    
    /* Remove borders from expander content area */
    [data-testid='stExpander'] > div > div {
        border: none !important;
    }
    
    /* Remove borders from code blocks inside expanders */
    [data-testid='stExpander'] [data-testid='stCodeBlock'] {
        border: none !important;
    }
    
    [data-testid='stExpander'] [data-testid='stCodeBlock'] pre {
        border: none !important;
    }
    
    /* Compact code blocks */
    code {
        padding: 0.15rem 0.4rem !important;
        font-size: 0.9em !important;
        margin: 0 !important;
    }
    
    /* Compact log display - reduce line spacing */
    pre {
        line-height: 1.4 !important;
        margin: 0.5rem 0 !important;
        padding: 0.75rem !important;
    }
    
    /* Reduce spacing in code blocks */
    [data-testid='stCodeBlock'] {
        margin: 0.3rem 0 !important;
    }
    
    [data-testid='stCodeBlock'] pre {
        line-height: 1.5 !important;
        padding: 0.5rem 0.75rem !important;
    }
    
    /* Reduce caption spacing */
    [data-testid='stCaption'] {
        margin: 0.2rem 0 !important;
        padding: 0 !important;
    }
    
    /* Dataframe styling - white background - ENHANCED */
    [data-testid='stDataFrame'] {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    [data-testid='stDataFrame'] > div {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    [data-testid='stDataFrame'] table {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-testid='stDataFrame'] thead {
        background: rgba(99, 102, 241, 0.08) !important;
        background-color: rgba(99, 102, 241, 0.08) !important;
        color: #1F2937 !important;
    }
    
    [data-testid='stDataFrame'] thead th {
        background: rgba(99, 102, 241, 0.08) !important;
        background-color: rgba(99, 102, 241, 0.08) !important;
        color: #1F2937 !important;
        font-weight: 600 !important;
        border-color: rgba(0, 0, 0, 0.1) !important;
    }
    
    [data-testid='stDataFrame'] tbody {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-testid='stDataFrame'] tbody tr {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-testid='stDataFrame'] tbody tr:nth-child(even) {
        background: #F9FAFB !important;
        background-color: #F9FAFB !important;
    }
    
    [data-testid='stDataFrame'] tbody tr:hover {
        background: rgba(99, 102, 241, 0.05) !important;
        background-color: rgba(99, 102, 241, 0.05) !important;
    }
    
    [data-testid='stDataFrame'] tbody td {
        background: transparent !important;
        background-color: transparent !important;
        color: #1F2937 !important;
        border-color: rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Ensure ALL table elements have white background */
    table {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    table thead {
        background: rgba(99, 102, 241, 0.08) !important;
        background-color: rgba(99, 102, 241, 0.08) !important;
        color: #1F2937 !important;
    }
    
    table tbody {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    table tbody tr {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    table tbody tr:nth-child(even) {
        background: #F9FAFB !important;
        background-color: #F9FAFB !important;
    }
    
    table tbody tr:hover {
        background: rgba(99, 102, 241, 0.05) !important;
        background-color: rgba(99, 102, 241, 0.05) !important;
    }
    
    table td, table th {
        color: #1F2937 !important;
        border-color: rgba(0, 0, 0, 0.1) !important;
    }
    
    table th {
        background: rgba(99, 102, 241, 0.08) !important;
        background-color: rgba(99, 102, 241, 0.08) !important;
        font-weight: 600 !important;
    }
    
    table td {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* NUCLEAR OPTION - Override ANY possible dark/black backgrounds */
    div[class*="stDataFrame"],
    div[class*="dataframe"],
    div[data-testid*="DataFrame"],
    section[class*="stDataFrame"],
    section[data-testid*="DataFrame"] {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    /* Override any Streamlit internal dark theme classes */
    [class*="stDataFrame"] table,
    [class*="dataframe"] table,
    div[class*="st-"] table {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    [class*="stDataFrame"] thead,
    [class*="dataframe"] thead,
    div[class*="st-"] thead {
        background: rgba(99, 102, 241, 0.08) !important;
        background-color: rgba(99, 102, 241, 0.08) !important;
    }
    
    [class*="stDataFrame"] tbody,
    [class*="dataframe"] tbody,
    div[class*="st-"] tbody {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    [class*="stDataFrame"] tr,
    [class*="dataframe"] tr,
    div[class*="st-"] tr {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    [class*="stDataFrame"] tr:nth-child(even),
    [class*="dataframe"] tr:nth-child(even),
    div[class*="st-"] tr:nth-child(even) {
        background: #F9FAFB !important;
        background-color: #F9FAFB !important;
    }
    
    [class*="stDataFrame"] td,
    [class*="dataframe"] td,
    div[class*="st-"] td {
        background: transparent !important;
        background-color: transparent !important;
        color: #1F2937 !important;
        /* 确保文字可见 */
        opacity: 1 !important;
        visibility: visible !important;
    }
    
    [class*="stDataFrame"] th,
    [class*="dataframe"] th,
    div[class*="st-"] th {
        background: rgba(99, 102, 241, 0.08) !important;
        background-color: rgba(99, 102, 241, 0.08) !important;
        color: #1F2937 !important;
        /* 确保文字可见 */
        opacity: 1 !important;
        visibility: visible !important;
    }
    
    /* 确保 DataFrame 容器内所有内容可见 */
    [data-testid='stDataFrame'] *,
    [class*='stDataFrame'] * {
        opacity: 1 !important;
        visibility: visible !important;
        display: revert !important;
    }
    
    /* 确保文字颜色对比度 */
    [data-testid='stDataFrame'] th,
    [data-testid='stDataFrame'] td {
        color: #1F2937 !important;
        font-size: 14px !important;
    }
    
    /* st.table 样式（备用显示方式） */
    [data-testid='stTable'] {
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        border-radius: 8px !important;
    }
    
    [data-testid='stTable'] table {
        background: #FFFFFF !important;
        width: 100% !important;
    }
    
    [data-testid='stTable'] th {
        background: rgba(99, 102, 241, 0.08) !important;
        color: #1F2937 !important;
        padding: 12px !important;
        font-weight: 600 !important;
    }
    
    [data-testid='stTable'] td {
        background: #FFFFFF !important;
        color: #1F2937 !important;
        padding: 10px !important;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05) !important;
    }
    
    [data-testid='stTable'] tr:nth-child(even) {
        background: #F9FAFB !important;
    }
    
    [data-testid='stTable'] tr:hover {
        background: rgba(99, 102, 241, 0.05) !important;
    }
    
    /* Override Streamlit's internal styling for data components */
    .stDataFrame,
    .dataframe-container,
    .dataframe {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    .stDataFrame table,
    .dataframe-container table,
    .dataframe table {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    /* Metrics should not have dark backgrounds */
    [data-testid='stMetric'] {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    [data-testid='stMetricValue'] {
        color: #1F2937 !important;
    }
    
    [data-testid='stMetricLabel'] {
        color: #6B7280 !important;
    }
    
    /* Ensure columns don't have dark backgrounds */
    [data-testid='column'] {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* Plotly charts container */
    .js-plotly-plot {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
</style>
<script>
(function() {
    // Only set background color, don't force visibility - allow Streamlit to control collapse/expand
    function styleSidebar() {
        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
        if (sidebar) {
            // Only set background color, let Streamlit handle display/visibility/width
            sidebar.style.backgroundColor = '#FFFFFF';
            
            // Ensure child elements have white background too
            const children = sidebar.querySelectorAll('*');
            children.forEach(child => {
                if (child.style) {
                    // Only override if it's a background color issue, not display/visibility
                    if (window.getComputedStyle(child).backgroundColor !== 'rgb(255, 255, 255)') {
                        // Don't force, just suggest
                    }
                }
            });
        }
    }
    
    // Run after DOM is ready to set background color
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', styleSidebar);
    } else {
        styleSidebar();
    }
    
    // Run after Streamlit renders
    setTimeout(styleSidebar, 100);
})();
</script>
""", unsafe_allow_html=True)

# 初始化 session state
if 'tasks' not in st.session_state:
    st.session_state.tasks = {}
if 'task_counter' not in st.session_state:
    st.session_state.task_counter = 0

# 后台任务管理器
class BackgroundTask:
    """后台任务管理器"""
    
    def __init__(self, task_id, task_name, cmd):
        self.task_id = task_id
        self.task_name = task_name
        self.cmd = cmd
        self.status = "running"  # running, completed, failed
        self.output_queue = queue.Queue()
        self.process = None
        self.thread = None
        self.start_time = datetime.now()
        self.end_time = None
        self.logs = []
        
    def start(self):
        """启动后台任务"""
        # 添加初始日志
        initial_log = f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Starting task: {self.task_name}"
        self.logs.append(initial_log)
        self.output_queue.put(initial_log)
        
        self.thread = threading.Thread(target=self._run_task, daemon=True)
        self.thread.start()
    
    def _run_task(self):
        """在后台线程中运行任务"""
        try:
            # 添加完整命令日志（用于调试）
            cmd_str = ' '.join(self.cmd)
            if len(cmd_str) > 200:
                debug_log = f"[{datetime.now().strftime('%H:%M:%S')}] 📝 Command: {cmd_str[:200]}..."
            else:
                debug_log = f"[{datetime.now().strftime('%H:%M:%S')}] 📝 Command: {cmd_str}"
            self.logs.append(debug_log)
            self.output_queue.put(debug_log)
            
            # 设置环境变量强制无缓冲输出
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # 分别捕获 stderr
                text=True,
                bufsize=0,  # 完全无缓冲
                universal_newlines=True,
                env=env  # 传递环境变量
            )
            
            # 进程启动后的日志
            started_log = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Process started (PID: {self.process.pid})"
            self.logs.append(started_log)
            self.output_queue.put(started_log)
            
            # 使用线程同时读取 stdout 和 stderr，避免阻塞
            def read_stream(stream, is_stderr=False):
                """在单独线程中读取流"""
                try:
                    for line in iter(stream.readline, ''):
                        if line:
                            timestamp = datetime.now().strftime('%H:%M:%S')
                            # 只对真正的错误添加 ERROR 前缀
                            # 排除：包含 INFO/WARNING 的行，或者只是分隔符/空行
                            stripped = line.strip()
                            
                            # 过滤分隔线（由重复的 =、-、_、*、# 组成）
                            if stripped and len(stripped) > 3 and all(c in '=-_*#' for c in stripped):
                                continue  # 跳过分隔线
                            
                            if is_stderr and stripped:
                                # 检查是否是真正的错误（包含错误关键词）
                                error_keywords = ['error', 'exception', 'traceback', 'failed', 'fatal']
                                is_real_error = (
                                    'INFO' not in line and 
                                    'WARNING' not in line and 
                                    any(keyword in line.lower() for keyword in error_keywords)  # 包含错误关键词
                                )
                                if is_real_error:
                                    log_line = f"[{timestamp}] ❌ ERROR: {line.rstrip()}"
                                else:
                                    log_line = f"[{timestamp}] {line.rstrip()}"
                            else:
                                log_line = f"[{timestamp}] {line.rstrip()}"
                            self.logs.append(log_line)
                            self.output_queue.put(log_line)
                except Exception as e:
                    error_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Stream read error: {e}"
                    self.logs.append(error_msg)
                    self.output_queue.put(error_msg)
            
            # 创建两个线程分别读取 stdout 和 stderr
            stdout_thread = threading.Thread(
                target=read_stream, 
                args=(self.process.stdout, False),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_stream, 
                args=(self.process.stderr, True),
                daemon=True
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            # 等待进程结束
            self.process.wait()
            
            # 等待读取线程完成（最多等待2秒）
            stdout_thread.join(timeout=2)
            # stderr_thread.join(timeout=2)
            
            self.end_time = datetime.now()
            
            if self.process.returncode == 0:
                self.status = "completed"
                complete_log = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Task completed successfully"
                self.logs.append(complete_log)
                self.output_queue.put(complete_log)
            else:
                self.status = "failed"
                fail_log = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Task failed (exit code: {self.process.returncode})"
                self.logs.append(fail_log)
                self.output_queue.put(fail_log)
                
                # 如果没有其他日志，添加提示
                if len(self.logs) <= 4:  # 只有启动日志
                    hint_log = f"[{datetime.now().strftime('%H:%M:%S')}] 💡 Hint: Process exited immediately. Check if the script has syntax errors or missing dependencies."
                    self.logs.append(hint_log)
                    self.output_queue.put(hint_log)
                
        except Exception as e:
            self.status = "failed"
            self.end_time = datetime.now()
            error_msg = f"❌ 任务异常: {str(e)}"
            self.logs.append(error_msg)
            self.output_queue.put(error_msg)
    
    def get_logs(self):
        """获取所有日志"""
        # 从队列中读取新日志
        while not self.output_queue.empty():
            try:
                line = self.output_queue.get_nowait()
                if line not in self.logs:
                    self.logs.append(line)
            except queue.Empty:
                break
        return self.logs
    
    def get_duration(self):
        """获取任务运行时长"""
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        else:
            duration = (datetime.now() - self.start_time).total_seconds()
        return duration
    
    def is_running(self):
        """检查任务是否正在运行"""
        return self.status == "running" and self.process and self.process.poll() is None
    
    def stop(self):
        """停止任务"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status = "stopped"
            self.end_time = datetime.now()
            self.output_queue.put("⚠️ 任务已手动停止")

# Sidebar Navigation
st.sidebar.markdown("# 📊 Navigation Menu")
page_radio = st.sidebar.radio(
    "Select Function",
    ["🏠 Home", "📈 Real-time Monitor", "🚀 Strategy Optimization", "📁 Strategy Management"],
    label_visibility="collapsed"
)

# Map display names to page keys
page_mapping_reverse = {
    "🏠 Home": "home",
    "📈 Real-time Monitor": "monitor",
    "🚀 Strategy Optimization": "optimization",
    "📁 Strategy Management": "management"
}
page = page_mapping_reverse.get(page_radio, "home")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Quick Info")

# Display strategy statistics
def load_strategies():
    """加载所有策略文件"""
    strategies_dir = Path("strategies")
    if not strategies_dir.exists():
        return []
    
    strategies = []
    for file in strategies_dir.glob("*.json"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            strategies.append({
                'filename': file.name,
                'symbol': file.name.split('_')[0],
                'name': data.get('name', 'Unknown'),
                'signal_weights': data.get('signal_weights', {}),
                'backtest_performance': data.get('backtest_performance', {}),
                'metadata': data.get('metadata', {}),
                'modified': datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'size': file.stat().st_size,
                'path': str(file)
            })
        except Exception as e:
            # Skip files with errors instead of showing error on every page load
            continue
    
    return sorted(strategies, key=lambda x: x['modified'], reverse=True)

def get_latest_strategy(symbol):
    """获取指定标的的最新策略"""
    strategies_dir = Path("strategies")
    if not strategies_dir.exists():
        return None
    
    pattern = f"{symbol}_*.json"
    found_files = list(strategies_dir.glob(pattern))
    
    if not found_files:
        return None
    
    # 按修改时间排序，获取最新的
    found_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest_file = found_files[0]
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return None

def delete_strategy(filepath):
    """删除策略文件"""
    try:
        path = Path(filepath)
        if path.exists():
            path.unlink()
            return True
        return False
    except Exception as e:
        return False

def save_strategy(symbol, strategy_data):
    """保存策略文件"""
    strategies_dir = Path("strategies")
    strategies_dir.mkdir(exist_ok=True)
    
    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_strategy_{timestamp}.json"
    filepath = strategies_dir / filename
    
    # 确保 metadata 中有 symbol
    if 'metadata' not in strategy_data:
        strategy_data['metadata'] = {}
    strategy_data['metadata']['symbol'] = symbol
    strategy_data['metadata']['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(strategy_data, f, indent=2, ensure_ascii=False)
    
    return filename

strategies = load_strategies()
symbols = list(set([s['symbol'] for s in strategies]))
st.sidebar.metric("Total Strategies", len(strategies))
st.sidebar.metric("Number of Symbols", len(symbols))

if strategies:
    latest = strategies[0]
    st.sidebar.info(f"**Latest Update**\n\n{latest['symbol']} - {latest['name']}\n\n{latest['modified']}")

# Map page keys to display names
page_mapping = {
    "home": "🏠 Home",
    "monitor": "📈 Real-time Monitor",
    "optimization": "🚀 Strategy Optimization",
    "management": "📁 Strategy Management"
}

# Get the display name for the current page
display_page = page_mapping.get(page, "🏠 Home")

# Debug: Uncomment to see current page in sidebar (for testing)
# st.sidebar.write(f"🔍 Debug: page='{page}', display_page='{display_page}'")

# ==================== Home ====================
if display_page == "🏠 Home":
    st.markdown('<h1 class="main-header">📊 QTSP - Quantitative Trading Strategy Platform</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    ### AI Powered Option Experimentation Platform！
    """)
    
    # 功能介绍
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🚀 Strategy Optimization</h3>
            <p>DeepSeek AI powered optimization, up to 10 iterations, automatically converges to the best configuration.</p>
            <ul>
                <li>AI-driven optimization</li>
                <li>Automatic version management</li>
                <li>Complete metadata recording</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>🔍 Strategy Scanning</h3>
            <p>Batch backtest multiple strategies across multiple symbols, automatically generate comparison reports and visual charts.</p>
            <ul>
                <li>Multiple symbol comparison</li>
                <li>8 professional charts</li>
                <li>Complete HTML report</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>📁 Strategy Management</h3>
            <p>View, edit, delete strategy files, intelligent version control system.</p>
            <ul>
                <li>Automatic version management</li>
                <li>Online editor</li>
                <li>Backup recovery</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 最近策略列表
    st.markdown("### 📋 Recently updated strategies")
    
    if strategies:
        df = pd.DataFrame([{
            'Symbol': s['symbol'],
            'Strategy Name': s['name'],
            'File Name': s['filename'],
            'Updated Time': s['modified'],
            'File Size': f"{s['size']} bytes"
        } for s in strategies[:10]])
        
        # 使用 st.table() 替代 st.dataframe()（在当前环境更可靠）
        st.table(df)
    else:
        st.info("No strategy files found, please run strategy optimization or manually add strategies.")


# ==================== Real-time Monitor ====================
elif display_page == "📈 Real-time Monitor":
    st.markdown('<h1 class="main-header">📈 Real-time Strategy Monitor</h1>', unsafe_allow_html=True)
    
    # Add custom CSS for the monitoring dashboard
    st.markdown("""
    <style>
        /* RockAlpha-inspired monitor cards */
        .monitor-card {
            background: #FFFFFF;
            padding: 1.5rem;
            border-radius: 12px;
            color: #1F2937;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
            border: 1px solid rgba(0, 0, 0, 0.1);
            transition: transform 0.2s ease;
        }
        
        .monitor-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        }
        
        .monitor-card-positive {
            background: #FFFFFF;
            padding: 1.5rem;
            border-radius: 12px;
            color: #10B981;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
            border: 1px solid rgba(16, 185, 129, 0.3);
            transition: transform 0.2s ease;
        }
        
        .monitor-card-positive:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.2), 0 2px 4px -1px rgba(16, 185, 129, 0.1);
        }
        
        .monitor-card-negative {
            background: #FFFFFF;
            padding: 1.5rem;
            border-radius: 12px;
            color: #EF4444;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
            border: 1px solid rgba(239, 68, 68, 0.3);
            transition: transform 0.2s ease;
        }
        
        .monitor-card-negative:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 6px -1px rgba(239, 68, 68, 0.2), 0 2px 4px -1px rgba(239, 68, 68, 0.1);
        }
        
        .big-number {
            font-size: 3rem;
            font-weight: bold;
            margin: 0.5rem 0;
            text-align: center;
            background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #A855F7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .subtitle-text {
            font-size: 1.2rem;
            opacity: 0.9;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        
        /* Data source indicator */
        .data-source {
            font-size: 0.9rem;
            opacity: 0.8;
            text-align: center;
            margin: 0.3rem 0;
            font-weight: 500;
        }
        
        /* Metric styling */
        [data-testid='stMetricValue'] {
            color: #A100FF !important;
        }
        
        /* Chart container */
        .chart-container {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 1rem;
            border: 1px solid rgba(0, 0, 0, 0.1);
        }
        
        /* Real-time pulsing indicator - RockAlpha style */
        .realtime-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #10B981;
            margin-right: 8px;
            animation: pulse 2s ease-in-out infinite;
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        }
        
        @keyframes pulse {
            0% {
                transform: scale(1);
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
            }
            50% {
                transform: scale(1.1);
                box-shadow: 0 0 0 8px rgba(16, 185, 129, 0);
            }
            100% {
                transform: scale(1);
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
            }
        }
        
        /* Value change animation */
        .value-updated {
            animation: flash-green 0.5s ease-in-out;
        }
        
        .value-updated-negative {
            animation: flash-red 0.5s ease-in-out;
        }
        
        @keyframes flash-green {
            0%, 100% { background-color: transparent; }
            50% { background-color: rgba(16, 185, 129, 0.2); }
        }
        
        @keyframes flash-red {
            0%, 100% { background-color: transparent; }
            50% { background-color: rgba(239, 68, 68, 0.2); }
        }
        
        /* Live badge */
        .live-badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            background: linear-gradient(135deg, #10B981 0%, #059669 100%);
            color: white;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 8px;
        }
        
        .live-badge .pulse-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: white;
            margin-right: 6px;
            animation: pulse-small 1.5s ease-in-out infinite;
        }
        
        @keyframes pulse-small {
            0%, 100% {
                opacity: 1;
                transform: scale(1);
            }
            50% {
                opacity: 0.5;
                transform: scale(0.8);
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Configuration
    monitor_start_date = "2025-04-01"
    
    # Initialize persistent cache
    cache_manager = MonitorCache()
    
    # Check API key availability
    has_api_key = bool(os.getenv('POLYGON_API_KEY'))
    
    # Real-time update status
    saved_results_file = Path("monitor_results.json")
    last_update_time = None
    if saved_results_file.exists():
        try:
            with open(saved_results_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                last_update_time = saved_data.get('generated_at', 'N/A')
        except:
            pass
    
    # Header with real-time indicator - compact layout
    col1, col2, col3 = st.columns([2.5, 1, 1])
    with col1:
        # Compact status display
        status_html = f"""
        <div style="display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem; background: #F9FAFB; border-radius: 8px; border: 1px solid rgba(0,0,0,0.1); margin-bottom: 0.5rem;">
            <span style="font-size: 1rem;">📅 <strong>Monitoring Period:</strong> {monitor_start_date} to <strong>Today</strong></span>
            {f'<span style="color: #666; margin-left: 0.5rem;">| 🕐 <strong>Last Update:</strong> {last_update_time}</span>' if last_update_time else ''}
        </div>
        """
        st.markdown(status_html, unsafe_allow_html=True)
    with col2:
        # Real-time indicator with pulsing effect
        auto_refresh = st.checkbox("🔄 Auto Refresh", value=True, key="monitor_auto_refresh")
    with col3:
        if st.button("🔄 Manual Update", use_container_width=True, key="monitor_update_btn"):
            # Force update for all symbols
            st.session_state['force_update'] = True
            st.rerun()
    
    # Try to load from saved results file first
    saved_results_file = Path("monitor_results.json")
    monitor_results = []
    saved_trades_map = {}  # Store trades data by symbol for later use
    
    if saved_results_file.exists():
        try:
            with open(saved_results_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                monitor_results = saved_data.get('results', [])
                saved_date = saved_data.get('generated_at', 'N/A')
                
            if monitor_results:
                # Compact success message
                success_html = f"""
                <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem; background: #ECFDF5; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3); margin-bottom: 1rem;">
                    <span style="color: #10B981; font-size: 1.1rem;">✅</span>
                    <span style="color: #1F2937;">Loaded <strong>{len(monitor_results)}</strong> symbols from saved results <span style="color: #666;">(Generated: {saved_date})</span></span>
                </div>
                """
                st.markdown(success_html, unsafe_allow_html=True)
                # Convert equity_curve from list of dicts to pandas Series and save trades data
                for result in monitor_results:
                    # Save trades data for this symbol
                    saved_trades_map[result['symbol']] = result.get('trades', [])
                    
                    equity_curve = result.get('equity_curve', [])
                    if equity_curve and isinstance(equity_curve, list):
                        # Convert list of {date, value} dicts to Series
                        dates = [item['date'] for item in equity_curve]
                        values = [item['value'] for item in equity_curve]
                        result['equity_curve'] = pd.Series(values, index=pd.to_datetime(dates))
        except Exception as e:
            st.warning(f"⚠️ Error loading saved results: {e}. Will load from cache instead.")
            monitor_results = []
    
    # If no saved results, load from cache (existing logic)
    if not monitor_results:
        # Load strategies
        strategies = load_strategies()
        
        if not strategies:
            st.warning("⚠️ No strategies found. Please run optimization first.")
            monitor_results = []
        else:
            # Group strategies by symbol and find best performing one
            symbol_best_strategies = {}
            
            for strategy in strategies:
                symbol = strategy['symbol']
                
                # Skip if already have a strategy for this symbol with better performance
                if symbol in symbol_best_strategies:
                    existing_return = symbol_best_strategies[symbol].get('backtest_performance', {}).get('total_return', -999)
                    current_return = strategy.get('backtest_performance', {}).get('total_return', -999)
                    if current_return <= existing_return:
                        continue
                
                symbol_best_strategies[symbol] = strategy
            
            st.markdown(f"### 🎯 Monitoring {len(symbol_best_strategies)} Symbols")
            
            # Load or update monitor data
            monitor_results = []
            force_update = st.session_state.get('force_update', False)
            
            with st.spinner('🔄 Loading strategy data from cache...'):
                for symbol, strategy in symbol_best_strategies.items():
                    try:
                        # Check if we need to update (once per day)
                        needs_update = cache_manager.needs_update(symbol) or force_update
                        
                        # Load cached data
                        cached_data = cache_manager.get_symbol_data(symbol)
                        equity_curve_series = cache_manager.get_equity_curve_series(symbol)
                        
                        if needs_update and has_api_key:
                            # Update today's data point
                            with st.spinner(f'🔄 Updating {symbol}...'):
                                # Load strategy config
                                with open(strategy['path'], 'r', encoding='utf-8') as f:
                                    strategy_config = json.load(f)
                                
                                # Run backtest for today only (or from last update to today)
                                backtest = OptionBacktest(initial_capital=10000, use_real_prices=True)
                                
                                params = strategy_config.get('params', {})
                                signal_weights = strategy_config.get('signal_weights', {})
                                
                                # Determine start date: use last update date or monitor_start_date
                                last_update = cache_manager.get_last_update_date(symbol)
                                if last_update:
                                    update_start_date = (datetime.strptime(last_update, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                                else:
                                    update_start_date = monitor_start_date
                                
                                end_date = datetime.now().strftime("%Y-%m-%d")
                                
                                result = backtest.run_backtest(
                                    symbol=symbol,
                                    start_date=update_start_date,
                                    end_date=end_date,
                                    strategy='auto',
                                    entry_signal=signal_weights,
                                    profit_target=params.get('profit_target', 5.0),
                                    stop_loss=params.get('stop_loss', -0.5),
                                    max_holding_days=params.get('max_holding_days', 30),
                                    position_size=params.get('position_size', 0.1)
                                )
                                
                                # Get today's final value
                                if len(result.equity_curve) > 0:
                                    today_value = result.equity_curve[-1]
                                    today_date = datetime.now().strftime('%Y-%m-%d')
                                    
                                    # Update equity curve with new data point
                                    cache_manager.update_equity_curve(symbol, {
                                        'date': today_date,
                                        'value': today_value
                                    })
                                    
                                    # Reload updated curve
                                    equity_curve_series = cache_manager.get_equity_curve_series(symbol)
                                    
                                    # Update cached metrics
                                    final_value = today_value
                                    total_return = (final_value - 10000) / 10000
                                    num_trades = len(result.trades)
                                    winning_trades = sum(1 for t in result.trades if t.pnl and t.pnl > 0)
                                    win_rate = (winning_trades / num_trades * 100) if num_trades > 0 else 0
                                    
                                    # Save updated metrics
                                    cached_data = cache_manager.get_symbol_data(symbol) or {}
                                    cached_data.update({
                                        'symbol': symbol,
                                        'strategy_name': strategy['name'],
                                        'total_return': total_return,
                                        'final_value': final_value,
                                        'num_trades': num_trades,
                                        'win_rate': win_rate,
                                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    })
                                    cache_manager.save_symbol_data(symbol, cached_data)
                        
                        # Load from cache
                        if cached_data:
                            monitor_results.append({
                                'symbol': symbol,
                                'strategy_name': cached_data.get('strategy_name', strategy['name']),
                                'total_return': cached_data.get('total_return', 0),
                                'final_value': cached_data.get('final_value', 10000),
                                'num_trades': cached_data.get('num_trades', 0),
                                'win_rate': cached_data.get('win_rate', 0),
                                'equity_curve': equity_curve_series,
                                'trades': saved_trades_map.get(symbol, []),  # Use saved trades data if available
                                'is_cached': True,
                                'last_updated': cached_data.get('last_updated', 'N/A')
                            })
                        else:
                            # No cache available, use strategy file data
                            backtest_perf = strategy.get('backtest_performance', {})
                            if backtest_perf and 'total_return' in backtest_perf:
                                total_return = backtest_perf.get('total_return', 0)
                                num_trades = backtest_perf.get('num_trades', 0)
                                win_rate = backtest_perf.get('win_rate', 0)
                                final_value = 10000 * (1 + total_return)
                                
                                # Create initial equity curve
                                today = datetime.now().strftime('%Y-%m-%d')
                                cache_manager.update_equity_curve(symbol, {
                                    'date': today,
                                    'value': final_value
                                })
                                
                                equity_curve_series = cache_manager.get_equity_curve_series(symbol)
                                
                                monitor_results.append({
                                    'symbol': symbol,
                                    'strategy_name': strategy['name'],
                                    'total_return': total_return,
                                    'final_value': final_value,
                                    'num_trades': num_trades,
                                    'win_rate': win_rate,
                                    'equity_curve': equity_curve_series,
                                    'trades': saved_trades_map.get(symbol, []),  # Use saved trades data if available
                                    'is_cached': True,
                                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                    except Exception as e:
                        st.error(f"❌ Error loading {symbol}: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
                        continue
            
            # Clear force update flag
            if force_update:
                st.session_state['force_update'] = False
            
            # Sort by return (best first)
            if monitor_results:
                monitor_results.sort(key=lambda x: x['total_return'], reverse=True)
        
    # Display results (whether from saved file or cache)
    if monitor_results:
        # Store previous values for comparison
        if 'monitor_previous_values' not in st.session_state:
            st.session_state.monitor_previous_values = {}
        
        # Display summary metrics with real-time indicator
        st.markdown("### 📊 Real-time Performance Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        total_symbols = len(monitor_results)
        avg_return = sum(r['total_return'] for r in monitor_results) / total_symbols if total_symbols > 0 else 0
        positive_symbols = sum(1 for r in monitor_results if r['total_return'] > 0)
        total_trades = sum(r['num_trades'] for r in monitor_results)
        
        # Calculate total portfolio value
        total_portfolio_value = sum(r['final_value'] for r in monitor_results)
        prev_total_value = st.session_state.monitor_previous_values.get('total_value', total_portfolio_value)
        
        with col1:
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.3rem;">🎯 Total Symbols</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #1F2937;">{total_symbols}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.3rem;">📈 Avg Return</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {'#10B981' if avg_return >= 0 else '#EF4444'};">
                    {avg_return:+.2%}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.3rem;">✅ Positive</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #1F2937;">{positive_symbols}/{total_symbols}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.3rem;">📊 Total Trades</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #1F2937;">{total_trades}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Total Portfolio Value with live indicator
        st.markdown("---")
        portfolio_change = total_portfolio_value - prev_total_value
        portfolio_change_pct = (portfolio_change / prev_total_value * 100) if prev_total_value > 0 else 0
        
        st.markdown(f"""
        <div style="text-align: center; padding: 1.5rem; background: #FFFFFF; border-radius: 12px; border: 1px solid rgba(0,0,0,0.1); margin: 1rem 0;">
            <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">
                TOTAL PORTFOLIO VALUE
                <span class="live-badge">
                    <span class="pulse-dot"></span>
                    LIVE
                </span>
            </div>
            <div style="font-size: 3rem; font-weight: bold; color: #1F2937; margin: 0.5rem 0;">
                ${total_portfolio_value:,.2f}
            </div>
            <div style="font-size: 1.2rem; color: {'#10B981' if portfolio_change >= 0 else '#EF4444'};">
                {portfolio_change:+.2f} ({portfolio_change_pct:+.2f}%)
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Update previous values
        st.session_state.monitor_previous_values = {
            'total_value': total_portfolio_value,
            'symbols': {r['symbol']: r['final_value'] for r in monitor_results}
        }
        
        st.markdown("---")
        
        # Display individual strategy cards
        st.markdown("### 📈 Live Strategy Performance")
        
        for idx, result in enumerate(monitor_results):
            card_class = "monitor-card-positive" if result['total_return'] > 0 else "monitor-card-negative"
            
            # Check if value changed (for animation)
            symbol = result['symbol']
            prev_value = st.session_state.monitor_previous_values.get('symbols', {}).get(symbol, result['final_value'])
            value_changed = abs(result['final_value'] - prev_value) > 0.01
            value_increased = result['final_value'] > prev_value
            
            # Add animation class if value changed
            animation_class = ""
            if value_changed and auto_refresh:
                animation_class = "value-updated" if value_increased else "value-updated-negative"
            
            # Display summary card at top (compact horizontal layout)
                st.markdown(f"""
            <div class="{card_class} {animation_class}" id="card-{symbol}" style="margin-bottom: 1rem;">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span class="realtime-indicator"></span>
                        <h2 style="margin:0; font-size: 1.5rem;">📊 {result['symbol']}</h2>
                        <span class="live-badge">
                            <span class="pulse-dot"></span>
                            LIVE
                        </span>
                    </div>
                    <div style="flex: 1; text-align: center;">
                        <p class="subtitle-text" style="margin: 0.2rem 0; font-size: 1rem;">{result['strategy_name']}</p>
                        <div class="big-number" style="font-size: 2rem; margin: 0.3rem 0;">{result['total_return']:+.2%}</div>
                        <p style="font-size: 0.95rem; margin: 0.3rem 0; color: #666;">
                        💰 ${result['final_value']:,.0f} | 
                        📊 {result['num_trades']} trades | 
                        🎯 {result['win_rate']:.1f}% win rate
                    </p>
                    </div>
                    <div style="text-align: right;">
                        <p style="font-size: 0.85rem; color: #666; margin: 0;">
                            Updated: {result.get('last_updated', 'N/A')}
                        </p>
                    </div>
                </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Display chart below (full width, larger height)
            # Check if equity_curve exists and is not empty
            equity_curve = result.get('equity_curve')
            if equity_curve is not None:
                # Convert to Series if it's not already
                if isinstance(equity_curve, pd.Series):
                    equity_series = equity_curve.copy()
                else:
                    equity_series = pd.Series(equity_curve)
                
                # Check if series is not empty
                if len(equity_series) > 0:
                    # Convert to DataFrame for easier handling
                    if isinstance(equity_curve, list):
                        # Convert list of {date, value} dicts to DataFrame
                        df = pd.DataFrame(equity_curve)
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.sort_values('date')
                        dates = df['date']
                        values = df['value']
                    else:
                        # Ensure index is datetime
                        if not isinstance(equity_series.index, pd.DatetimeIndex):
                            equity_series.index = pd.to_datetime(equity_series.index)
                        dates = equity_series.index
                        values = equity_series.values
                    
                    # Determine colors based on return
                    line_color = '#10B981' if result['total_return'] > 0 else '#EF4444'
                    fill_color = 'rgba(16, 185, 129, 0.3)' if result['total_return'] > 0 else 'rgba(239, 68, 68, 0.3)'
                    
                    # Create interactive Plotly chart
                    fig = go.Figure()
                    
                    # Add equity curve line
                    fig.add_trace(go.Scatter(
                        x=dates,
                        y=values,
                        mode='lines',
                        name='Portfolio Value',
                        line=dict(
                            color=line_color,
                            width=3
                        ),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                    'Date: %{x|%Y-%m-%d}<br>' +
                                    'Value: $%{y:,.2f}<br>' +
                                    '<extra></extra>',
                        fill='tonexty',
                        fillcolor=fill_color
                    ))
                    
                    # Add baseline (initial capital)
                    fig.add_hline(
                        y=10000,
                        line_dash="dash",
                        line_color="#A100FF",
                        opacity=0.5,
                        annotation_text="Initial Capital",
                        annotation_position="right"
                    )
                    
                    # Update layout for white background theme
                    fig.update_layout(
                        title={
                            'text': f'{result["symbol"]} Equity Curve',
                            'x': 0.5,
                            'xanchor': 'center',
                            'font': {'size': 16, 'color': '#1F2937'}
                        },
                        xaxis=dict(
                            title=dict(text='Date', font=dict(color='#1F2937')),
                            tickfont=dict(color='#1F2937'),
                            gridcolor='rgba(0,0,0,0.1)',
                            showgrid=True
                        ),
                        yaxis=dict(
                            title=dict(text='Portfolio Value ($)', font=dict(color='#1F2937')),
                            tickfont=dict(color='#1F2937'),
                            gridcolor='rgba(0,0,0,0.1)',
                            showgrid=True,
                            tickformat='$,.0f'
                        ),
                        plot_bgcolor='#FFFFFF',
                        paper_bgcolor='#FFFFFF',
                        hovermode='x unified',
                        height=500,
                        margin=dict(l=60, r=30, t=40, b=60),
                        showlegend=False
                    )
                    
                    # Display interactive chart
                    st.plotly_chart(fig, use_container_width=True, config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': f'{result["symbol"]}_equity_curve',
                            'height': 600,
                            'width': 1200,
                            'scale': 2
                        }
                    })
                else:
                    st.info("No equity curve data available")
            
            # Expandable trade details
            with st.expander(f"📝 View {result['num_trades']} Trades for {result['symbol']}"):
                if result.get('trades') and len(result['trades']) > 0:
                    trades_data = []
                    for i, trade in enumerate(result['trades'], 1):
                        # 处理两种格式：Trade 对象或字典
                        if isinstance(trade, dict):
                            # 从 JSON 加载的字典格式
                            trades_data.append({
                                '#': i,
                                'Entry': trade.get('entry_date', 'N/A'),
                                'Exit': trade.get('exit_date', '—') if trade.get('exit_date') else '—',
                                'Type': trade.get('strategy', 'N/A').upper() if trade.get('strategy') else 'N/A',
                                'Strike': f"${trade.get('strike', 0):.2f}" if trade.get('strike') is not None else 'N/A',
                                'Entry Price': f"${trade.get('entry_price', 0):.2f}",
                                'Exit Price': f"${trade.get('exit_price', 0):.2f}" if trade.get('exit_price') else '—',
                                'P&L': f"${trade.get('pnl', 0):+,.2f}" if trade.get('pnl') is not None else '—',
                                'Return': f"{trade.get('pnl_pct', 0):+.2%}" if trade.get('pnl_pct') is not None else '—',
                                'Status': trade.get('status', 'N/A').upper() if trade.get('status') else 'N/A'
                            })
                        else:
                            # Trade 对象格式
                            trades_data.append({
                                '#': i,
                                'Entry': trade.entry_date,
                                'Exit': trade.exit_date if trade.exit_date else '—',
                                'Type': trade.strategy.upper() if hasattr(trade, 'strategy') else 'N/A',
                                'Strike': f"${trade.strike:.2f}" if hasattr(trade, 'strike') else 'N/A',
                                'Entry Price': f"${trade.entry_price:.2f}",
                                'Exit Price': f"${trade.exit_price:.2f}" if trade.exit_price else '—',
                                'P&L': f"${trade.pnl:+,.2f}" if trade.pnl is not None else '—',
                                'Return': f"{trade.pnl_pct:+.2%}" if trade.pnl_pct is not None else '—',
                                'Status': trade.status.upper() if hasattr(trade, 'status') else 'N/A'
                            })
                    
                    trades_df = pd.DataFrame(trades_data)
                    
                    # 直接使用 st.table() 替代 st.dataframe()
                    # st.dataframe() 在当前环境中渲染为空白，改用更可靠的 st.table()
                    st.table(trades_df)
                elif result.get('num_trades', 0) > 0:
                    st.warning(f"⚠️ Trade details not available. {result['num_trades']} trades were executed, but detailed records were not saved.")
                    st.info("💡 **Tip:** Click '🔄 Manual Update' button above to refresh and save trade details, or wait for the automatic update (runs every 15 minutes).")
                else:
                    st.info("No trades executed in this period")
        
        # Performance comparison table
        st.markdown("---")
        st.markdown("### 📊 Performance Comparison")
        
        comparison_df = pd.DataFrame([{
            'Symbol': r['symbol'],
            'Strategy': r['strategy_name'],
            'Return': f"{r['total_return']:+.2%}",
            'Final Value': f"${r['final_value']:,.0f}",
            'Trades': r['num_trades'],
            'Win Rate': f"{r['win_rate']:.1f}%"
        } for r in monitor_results])
        
        # 使用 st.table() 显示（st.dataframe 在某些环境渲染有问题）
        st.table(comparison_df)
    else:
        st.info("💡 No monitor results available. Data will appear after the first update cycle.")
    
        # Auto-refresh logic for real-time updates
    if auto_refresh:
            # Check if monitor_results.json was recently updated (within last 16 minutes)
            if saved_results_file.exists():
                file_mtime = saved_results_file.stat().st_mtime
                time_since_update = time.time() - file_mtime
                
                # Refresh every 15 seconds to check for updates
                if time_since_update < 960:  # 16 minutes
                    time.sleep(15)
                    st.rerun()
                else:
                    # No recent updates, refresh every 30 seconds
                    time.sleep(30)
                    st.rerun()
            else:
                # File doesn't exist, refresh every 30 seconds
                time.sleep(30)
                st.rerun()


# ==================== 策略优化 ====================
elif display_page == "🚀 Strategy Optimization":
    st.markdown('<h1 class="main-header">🚀 Strategy Optimization</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Use DeepSeek AI to automatically optimize strategy parameters, generate versioned strategy files with timestamps.
    **Background tasks will continue to run, you can switch to other tabs to view progress.**
    """)
    
    # 显示当前运行的优化任务
    running_tasks = {tid: task for tid, task in st.session_state.tasks.items() 
                    if task.status == "running" and tid.startswith("opt_")}
    
    if running_tasks:
        st.info(f"⏳ There are {len(running_tasks)} optimization tasks running")
        for task_id, task in running_tasks.items():
            with st.expander(f"🔄 {task.task_name} (Running {task.get_duration():.0f} seconds)", expanded=False):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**Status:** {task.status}")
                    st.write(f"**Start Time:** {task.start_time.strftime('%H:%M:%S')}")
                with col2:
                    if st.button("⏹️ Stop", key=f"stop_opt_{task_id}"):
                        task.stop()
                        st.rerun()
    
    # 单标的优化表单
    st.markdown("### 📊 Optimize Strategy")
    st.markdown("Generate optimized strategy for a specific symbol.")
    
    with st.form("single_optimization_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("Symbol", value="BABA", help="e.g.: BABA, NVDA, AAPL")
            start_date = st.date_input("Backtest Start Date", value=pd.to_datetime("2025-01-01"), key="single_start")
            max_iter = st.slider("Max Iterations", 1, 20, 10, key="single_iter")
        
        with col2:
            st.write("")  # 占位
            end_date = st.date_input("Backtest End Date", value=pd.to_datetime("2025-12-01"), key="single_end")
            threshold = st.slider("Convergence Threshold", 0.01, 0.2, 0.05, 0.01, key="single_threshold")
        
        submitted = st.form_submit_button("🚀 Start Optimization", use_container_width=True)
    
    if submitted:
        if not symbol:
            st.error("Please enter the symbol code")
        else:
            # 创建后台任务
            st.session_state.task_counter += 1
            task_id = f"opt_{st.session_state.task_counter}"
            
            cmd = [
                sys.executable,
                "-u",  # 无缓冲模式，确保实时输出日志
                "run_iterative_optimization.py",
                "--symbol", symbol,
                "--start", start_date.strftime("%Y-%m-%d"),
                "--end", end_date.strftime("%Y-%m-%d"),
                "--max-iter", str(max_iter),
                "--threshold", str(threshold)
            ]
            
            task = BackgroundTask(
                task_id=task_id,
                task_name=f"Optimize {symbol}",
                cmd=cmd
            )
            
            st.session_state.tasks[task_id] = task
            task.start()
            
            st.success(f"✅ Task started! Task ID: {task_id}")
            st.info("💡 You can switch to other pages, the task will continue to run in the background")
            st.rerun()
    
    # 显示所有优化任务
    st.markdown("---")
    st.markdown("### 📋 Optimization Task List")
    
    # 显示所有优化任务
    opt_tasks = {tid: task for tid, task in st.session_state.tasks.items() 
                 if tid.startswith("opt_")}
    
    if not opt_tasks:
        st.info("No optimization tasks found")
    else:
        # 按状态分组
        for task_id, task in list(opt_tasks.items()):
            status_icon = {
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "stopped": "⏹️"
            }.get(task.status, "❓")
            
            with st.expander(
                f"{status_icon} {task.task_name} | {task.status.upper()} | 开始于 {task.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                expanded=(task.status == "running")
            ):
                # 紧凑布局 - 使用表格形式
                info_col1, info_col2, info_col3 = st.columns([2.5, 2.5, 1])
                
                with info_col1:
                    st.markdown(f"**Task ID:** `{task_id}`<br>**Status:** `{task.status.upper()}`", unsafe_allow_html=True)
                
                with info_col2:
                    end_time_str = task.end_time.strftime('%Y-%m-%d %H:%M:%S') if task.end_time else "—"
                    st.markdown(f"**Start:** {task.start_time.strftime('%Y-%m-%d %H:%M:%S')}<br>**End:** {end_time_str}<br>**Run Time:** {task.get_duration():.1f}s", unsafe_allow_html=True)
                
                with info_col3:
                    if task.status == "running":
                        if st.button("⏹️ Stop", key=f"stop_task_{task_id}", use_container_width=True):
                            task.stop()
                            st.rerun()
                    else:
                        if st.button("🗑️ Delete", key=f"del_task_{task_id}", use_container_width=True):
                            del st.session_state.tasks[task_id]
                            st.rerun()
                
                # 实时日志 - 使用 checkbox 控制显示，避免自动刷新时关闭
                logs = task.get_logs()
                if logs:
                    display_logs = logs[-50:] if len(logs) > 50 else logs
                    log_text = "\n".join(display_logs)
                    
                    # 使用 session_state 保存显示状态
                    log_show_key = f"log_show_{task_id}"
                    if log_show_key not in st.session_state:
                        st.session_state[log_show_key] = False
                    
                    # 使用 checkbox 控制显示
                    show_logs = st.checkbox(
                        f"📜 Logs ({len(display_logs)}/{len(logs)})",
                        value=st.session_state[log_show_key],
                        key=f"log_checkbox_{task_id}",
                        help="Click to show/hide logs"
                    )
                    st.session_state[log_show_key] = show_logs
                    
                    if show_logs:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.caption(f"Showing last {len(display_logs)} entries")
                        with col2:
                            if len(logs) > 50:
                                full_log_text = "\n".join(logs)
                                st.download_button(
                                    "📥 Download",
                                    data=full_log_text,
                                    file_name=f"{task_id}_logs.txt",
                                    mime="text/plain",
                                    key=f"opt_save_logs_{task_id}",
                                    use_container_width=True
                                )
                        
                        # 使用纯文本显示，外部加边框
                        log_html = f"""
                        <div style="
                            border: 1px solid rgba(0, 0, 0, 0.1);
                            border-radius: 8px;
                            padding: 1rem;
                            background: #FFFFFF;
                            font-family: 'Courier New', monospace;
                            font-size: 13px;
                            line-height: 1.6;
                            color: #1F2937;
                            max-height: 500px;
                            overflow-y: auto;
                            white-space: pre-wrap;
                            word-wrap: break-word;
                        ">
{log_text}
                        </div>
                        """
                        st.markdown(log_html, unsafe_allow_html=True)
                else:
                    st.caption(f"⏳ Waiting for logs... ({task.get_duration():.1f}s)")
                
                # 自动刷新（运行中的任务始终刷新，无论是否有日志）
                if task.status == "running":
                    time.sleep(0.5)
                    st.rerun()
                
                # 如果任务完成，显示结果
                if task.status == "completed":
                    st.success("🎉 Mission completed successfully!")
                    
                    # 尝试获取生成的策略
                    symbol = task.task_name.split()[-1]  # 从任务名称提取标的
                    latest = get_latest_strategy(symbol)
                    if latest:
                        # 使用白色主题显示JSON
                        json_str = json.dumps(latest, indent=2, ensure_ascii=False)
                        json_html = f"""
                        <div style="
                            border: 1px solid rgba(0, 0, 0, 0.1);
                            border-radius: 8px;
                            padding: 1rem;
                            background: #FFFFFF;
                            font-family: 'Courier New', monospace;
                            font-size: 13px;
                            line-height: 1.6;
                            color: #1F2937;
                            max-height: 500px;
                            overflow-y: auto;
                            white-space: pre-wrap;
                            word-wrap: break-word;
                        ">
{json_str}
                        </div>
                        """
                        st.markdown(json_html, unsafe_allow_html=True)
                        st.download_button(
                            "💾 Download Strategy File",
                            data=json.dumps(latest, indent=2, ensure_ascii=False),
                            file_name=f"{symbol}_strategy.json",
                            mime="application/json",
                            key=f"download_{task_id}"
                        )


# ==================== Strategy Management ====================
elif display_page == "📁 Strategy Management":
    st.markdown('<h1 class="main-header">📁 Strategy Management</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Manage your trading strategies: browse, compare, edit, and perform batch scanning with selected strategies.
    """)
    
    # 创建标签页
    mgmt_tab1, mgmt_tab2, mgmt_tab3 = st.tabs(["📋 Strategy List", "⚖️ Strategy Comparison", "🎯 Custom Scan"])
    
    # ==================== Tab 1: Strategy List ====================
    with mgmt_tab1:
        st.markdown("### 📋 Strategy Library")
        
        # 过滤选项
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            filter_symbol = st.selectbox("Select Symbol", ["All"] + symbols, key="filter_symbol_list")
        with col2:
            sort_by = st.selectbox("Sort by", ["Modified Time", "Symbol", "File Name"])
        with col3:
            st.write("")
            st.write("")
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        # Filter strategies
        filtered_strategies = strategies
        if filter_symbol != "All":
            filtered_strategies = [s for s in strategies if s['symbol'] == filter_symbol]
        
        # Sort
        if sort_by == "Symbol":
            filtered_strategies = sorted(filtered_strategies, key=lambda x: x['symbol'])
        elif sort_by == "File Name":
            filtered_strategies = sorted(filtered_strategies, key=lambda x: x['filename'])
        
        st.markdown(f"**Found {len(filtered_strategies)} strategies**")
        
        if not filtered_strategies:
            st.info("No strategy files found")
        else:
            for strategy in filtered_strategies:
                with st.expander(f"**{strategy['symbol']}** - {strategy['name']} ({strategy['filename']})"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"""
                        - **File Name**: {strategy['filename']}
                        - **Symbol**: {strategy['symbol']}
                        - **Strategy Name**: {strategy['name']}
                        - **Updated Time**: {strategy['modified']}
                        - **File Size**: {strategy['size']} bytes
                        """)
                        
                        # Display metadata
                        if strategy['metadata']:
                            st.markdown("**Metadata**:")
                            meta = strategy['metadata']
                            if 'best_return' in meta:
                                st.write(f"- Return: {meta['best_return']:+.2%}" if isinstance(meta['best_return'], (int, float)) else f"- Return: {meta['best_return']}")
                            if 'generated_at' in meta:
                                st.write(f"- Generated At: {meta['generated_at']}")
                            if 'backtest_period' in meta:
                                st.write(f"- Backtest Period: {meta['backtest_period']}")
                        
                        # Display backtest performance
                        if strategy.get('backtest_performance'):
                            st.markdown("**Backtest Performance**:")
                            perf = strategy['backtest_performance']
                            if isinstance(perf, dict):
                                # 单标的性能
                                if 'total_return' in perf:
                                    cols = st.columns(4)
                                    cols[0].metric("Return", f"{perf.get('total_return', 0):+.2%}")
                                    cols[1].metric("Win Rate", f"{perf.get('win_rate', 0):.1%}")
                                    cols[2].metric("Sharpe", f"{perf.get('sharpe_ratio', 0):.2f}")
                                    cols[3].metric("Trades", perf.get('num_trades', 0))
                                else:
                                    # 多标的性能
                                    for sym, p in perf.items():
                                        st.write(f"**{sym}**: Return {p.get('total_return', 0):+.2%}, Win Rate {p.get('win_rate', 0):.1%}, Trades {p.get('num_trades', 0)}")
                    
                    with col2:
                        # Action buttons
                        if st.button("📝 Edit", key=f"edit_{strategy['filename']}", use_container_width=True):
                            st.session_state['editing'] = strategy['path']
                        
                        if st.button("💾 Download", key=f"download_{strategy['filename']}", use_container_width=True):
                            with open(strategy['path'], 'r', encoding='utf-8') as f:
                                content = f.read()
                            st.download_button(
                                "Confirm Download",
                                data=content,
                                file_name=strategy['filename'],
                                mime="application/json",
                                key=f"dl_{strategy['filename']}"
                            )
                        
                        if st.button("🗑️ Delete", key=f"delete_{strategy['filename']}", use_container_width=True, type="secondary"):
                            if delete_strategy(strategy['path']):
                                st.success("Deleted successfully")
                                st.rerun()
                    
                    # JSON content - 使用白色主题显示
                    try:
                        with open(strategy['path'], 'r', encoding='utf-8') as f:
                            content = json.load(f)
                        
                        # 格式化JSON为字符串
                        json_str = json.dumps(content, indent=2, ensure_ascii=False)
                        
                        # 使用自定义HTML显示，白色背景
                        json_html = f"""
                        <div style="
                            border: 1px solid rgba(0, 0, 0, 0.1);
                            border-radius: 8px;
                            padding: 1rem;
                            background: #FFFFFF;
                            font-family: 'Courier New', monospace;
                            font-size: 13px;
                            line-height: 1.6;
                            color: #1F2937;
                            max-height: 500px;
                            overflow-y: auto;
                            white-space: pre-wrap;
                            word-wrap: break-word;
                        ">
{json_str}
                        </div>
                        """
                        st.markdown(json_html, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Failed to read file: {e}")
        
        # Editor
        if 'editing' in st.session_state:
            st.markdown("---")
            st.markdown("### ✏️ Edit Strategy")
            
            filepath = st.session_state['editing']
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                edited = st.text_area(
                    "JSON Content",
                    value=content,
                    height=400,
                    help="Please ensure JSON format is correct"
                )
                
                col1, col2, col3 = st.columns([1, 1, 4])
                with col1:
                    if st.button("💾 Save", use_container_width=True):
                        try:
                            # Validate JSON
                            json.loads(edited)
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(edited)
                            st.success("Saved successfully")
                            del st.session_state['editing']
                            st.rerun()
                        except json.JSONDecodeError as e:
                            st.error(f"JSON format error: {e}")
                
                with col2:
                    if st.button("❌ Cancel", use_container_width=True):
                        del st.session_state['editing']
                        st.rerun()
            
            except Exception as e:
                st.error(f"Failed to read file: {e}")
                del st.session_state['editing']
        
        # Upload new strategy
        st.markdown("---")
        st.markdown("### ➕ Upload New Strategy")
        
        uploaded_file = st.file_uploader("Select JSON file", type=['json'], key="upload_strategy_list")
        if uploaded_file:
            try:
                content = json.loads(uploaded_file.read().decode('utf-8'))
                
                symbol = st.text_input("Symbol", value=content.get('metadata', {}).get('symbol', ''), key="upload_symbol_list")
                
                if st.button("📤 Upload"):
                    if symbol:
                        filename = save_strategy(symbol, content)
                        st.success(f"Uploaded successfully: {filename}")
                        st.rerun()
                    else:
                        st.error("Please enter the symbol")
            except Exception as e:
                st.error(f"File format error: {e}")
    
    # ==================== Tab 2: Strategy Comparison ====================
    with mgmt_tab2:
        st.markdown("### ⚖️ Strategy Comparison")
        st.markdown("Select multiple strategies to compare their performance metrics side by side.")
        
        if not strategies:
            st.info("No strategies available for comparison")
        else:
            # 策略选择
            st.markdown("#### Select Strategies to Compare (2-5 strategies)")
            
            # 创建策略选择列表
            strategy_options = {}
            for s in strategies:
                key = f"{s['symbol']} - {s['name']} ({s['filename']})"
                strategy_options[key] = s
            
            selected_keys = st.multiselect(
                "Choose strategies",
                options=list(strategy_options.keys()),
                max_selections=5,
                help="Select 2 to 5 strategies to compare"
            )
            
            if len(selected_keys) < 2:
                st.info("Please select at least 2 strategies to compare")
            else:
                selected_strategies = [strategy_options[key] for key in selected_keys]
                
                st.markdown(f"**Comparing {len(selected_strategies)} strategies**")
                
                # 创建对比表格
                comparison_data = []
                for strat in selected_strategies:
                    row = {
                        "Strategy": strat['name'],
                        "Symbol": strat['symbol'],
                        "File": strat['filename'],
                        "Modified": strat['modified']
                    }
                    
                    # 添加元数据
                    if strat.get('metadata'):
                        meta = strat['metadata']
                        if 'best_return' in meta and isinstance(meta['best_return'], (int, float)):
                            row["Best Return"] = f"{meta['best_return']:+.2%}"
                        if 'backtest_period' in meta:
                            row["Period"] = meta['backtest_period']
                    
                    # 添加回测性能
                    if strat.get('backtest_performance'):
                        perf = strat['backtest_performance']
                        if isinstance(perf, dict) and 'total_return' in perf:
                            row["Total Return"] = f"{perf.get('total_return', 0):+.2%}"
                            row["Win Rate"] = f"{perf.get('win_rate', 0):.1%}"
                            row["Sharpe Ratio"] = f"{perf.get('sharpe_ratio', 0):.2f}"
                            row["Max Drawdown"] = f"{perf.get('max_drawdown', 0):.2%}"
                            row["Num Trades"] = perf.get('num_trades', 0)
                            row["Avg Win"] = f"${perf.get('avg_win', 0):,.0f}"
                            row["Avg Loss"] = f"${perf.get('avg_loss', 0):,.0f}"
                    
                    comparison_data.append(row)
                
                # 显示对比表格
                df_comparison = pd.DataFrame(comparison_data)
                st.table(df_comparison)
                
                # 显示信号权重对比
                st.markdown("#### Signal Weights Comparison")
                
                signal_comparison = {}
                for strat in selected_strategies:
                    strat_label = f"{strat['symbol']}_{strat['name']}"
                    if strat.get('signal_weights'):
                        for signal, weight in strat['signal_weights'].items():
                            if signal not in signal_comparison:
                                signal_comparison[signal] = {}
                            signal_comparison[signal][strat_label] = weight
                
                if signal_comparison:
                    signal_df = pd.DataFrame(signal_comparison).T
                    signal_df = signal_df.fillna(0)
                    
                    # 使用柱状图显示
                    st.bar_chart(signal_df)
                    
                    # 也显示表格
                    with st.expander("View Signal Weights Table"):
                        st.table(signal_df)
                
                # 下载对比报告
                st.markdown("---")
                if st.button("📥 Download Comparison Report", use_container_width=True):
                    report_data = {
                        "comparison_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "strategies": comparison_data,
                        "signal_weights": signal_comparison
                    }
                    report_json = json.dumps(report_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        "Download JSON",
                        data=report_json,
                        file_name=f"strategy_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
    
    # ==================== Tab 3: Custom Scan ====================
    with mgmt_tab3:
        st.markdown("### 🎯 Custom Strategy Scan")
        st.markdown("Select specific strategies and symbols to perform a custom batch backtest scan.")
        
        if not strategies:
            st.info("No strategies available. Please create or upload strategies first.")
        else:
            st.markdown("#### Configure Custom Scan")
            st.markdown("*Select symbols and strategies - all combinations will be tested*")
            
            # 按标的分组策略
            strategies_by_symbol = {}
            for s in strategies:
                sym = s['symbol']
                if sym not in strategies_by_symbol:
                    strategies_by_symbol[sym] = []
                strategies_by_symbol[sym].append(s)
            
            # Step 1: 选择标的
            st.markdown("**Step 1: Select Symbols to Test**")
            test_symbols = st.multiselect(
                "Choose symbols",
                options=symbols,
                default=symbols[:3] if len(symbols) >= 3 else symbols,
                help="Select one or more symbols for backtesting",
                key="custom_scan_symbols"
            )
            
            # Step 2: 选择策略（支持多选）
            st.markdown("**Step 2: Select Strategies to Test**")
            st.caption("💡 You can select multiple strategies - each will be tested against each symbol")
            
            selected_strategies = []
            symbol_strategy_pairs = []
            
            if test_symbols:
                # 为每个标的展示可用策略
                strategy_selection_mode = st.radio(
                    "Strategy Selection Mode",
                    options=["Quick Select (Same strategies for all symbols)", 
                             "Advanced (Different strategies per symbol)"],
                    key="strategy_mode",
                    horizontal=True
                )
                
                if strategy_selection_mode.startswith("Quick Select"):
                    # 快速模式：选择策略，应用到所有标的
                    st.markdown("**Select strategies to test across all symbols:**")
                    
                    # 收集所有可用策略（去重）
                    all_strategies = {}
                    for sym in test_symbols:
                        sym_strategies = strategies_by_symbol.get(sym, [])
                        for s in sym_strategies:
                            key = f"{s['filename']}"
                            if key not in all_strategies:
                                all_strategies[key] = s
                    
                    # 添加通用策略
                    universal_strategies = [s for s in strategies if s.get('metadata', {}).get('type') == 'universal']
                    for s in universal_strategies:
                        key = f"{s['filename']}"
                        if key not in all_strategies:
                            all_strategies[key] = s
                    
                    if all_strategies:
                        strategy_list = list(all_strategies.values())
                        strategy_display = [f"{s['name']} ({s['symbol']}) - {s['filename']}" for s in strategy_list]
                        
                        selected_indices = st.multiselect(
                            "Strategies",
                            options=range(len(strategy_list)),
                            default=[0] if len(strategy_list) > 0 else [],
                            format_func=lambda i: strategy_display[i],
                            key="quick_strategies"
                        )
                        
                        # 生成所有组合
                        for sym in test_symbols:
                            for idx in selected_indices:
                                symbol_strategy_pairs.append({
                                    'symbol': sym,
                                    'strategy': strategy_list[idx]
                                })
                    else:
                        st.warning("No strategies available for the selected symbols")
                
                else:
                    # 高级模式：为每个标的单独选择策略
                    st.markdown("**Select strategies for each symbol:**")
                    
                    for test_sym in test_symbols:
                        with st.expander(f"**{test_sym}** - Select Strategies", expanded=False):
                            # 获取该标的可用的策略
                            available_strategies = strategies_by_symbol.get(test_sym, [])
                            
                            # 添加通用策略
                            universal_strategies = [s for s in strategies if s.get('metadata', {}).get('type') == 'universal']
                            all_available = available_strategies + universal_strategies
                            
                            if not all_available:
                                st.warning(f"No strategies available for {test_sym}")
                                continue
                            
                            # 策略多选
                            strategy_display = [f"{s['name']} - {s['filename']}" for s in all_available]
                            selected_indices = st.multiselect(
                                f"Strategies for {test_sym}",
                                options=range(len(all_available)),
                                default=[0] if len(all_available) > 0 else [],
                                format_func=lambda i: strategy_display[i],
                                key=f"strat_select_{test_sym}",
                                label_visibility="collapsed"
                            )
                            
                            # 显示选中策略的信息
                            if selected_indices:
                                st.caption(f"**{len(selected_indices)} strateg{'ies' if len(selected_indices) > 1 else 'y'} selected:**")
                                for idx in selected_indices:
                                    selected_strategy = all_available[idx]
                                    symbol_strategy_pairs.append({
                                        'symbol': test_sym,
                                        'strategy': selected_strategy
                                    })
                                    
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.caption(f"📊 {selected_strategy['name']}")
                                    with col2:
                                        perf = selected_strategy.get('backtest_performance', {})
                                        if perf:
                                            returns = perf.get('total_return', 0) * 100
                                            st.caption(f"💰 {returns:+.1f}%")
                                    with col3:
                                        perf = selected_strategy.get('backtest_performance', {})
                                        if perf:
                                            win_rate = perf.get('win_rate', 0) * 100
                                            st.caption(f"🎯 {win_rate:.1f}%")
            else:
                st.info("👆 Please select at least one symbol to continue")
            
            st.markdown("---")
            st.markdown("#### Scan Configuration")
            
            col1, col2 = st.columns(2)
            with col1:
                scan_start = st.date_input(
                    "Start Date",
                    value=pd.to_datetime("2025-01-01"),
                    key="custom_scan_start"
                )
            with col2:
                scan_end = st.date_input(
                    "End Date",
                    value=pd.to_datetime("2025-12-01"),
                    key="custom_scan_end"
                )
            
            # 显示选择摘要
            st.markdown("**Step 3: Review & Launch**")
            
            if symbol_strategy_pairs:
                # 统计唯一的标的和策略数量
                unique_symbols = set([p['symbol'] for p in symbol_strategy_pairs])
                unique_strategies = set([p['strategy']['filename'] for p in symbol_strategy_pairs])
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Symbols", len(unique_symbols))
                col2.metric("Strategies", len(unique_strategies))
                col3.metric("Total Tests", len(symbol_strategy_pairs))
                
                # 显示所有组合
                with st.expander("📋 View All Test Combinations", expanded=False):
                    for i, pair in enumerate(symbol_strategy_pairs, 1):
                        st.caption(f"{i}. **{pair['symbol']}** × {pair['strategy']['name']}")
            
            # 启动扫描按钮
            if st.button("🚀 Start Custom Scan", type="primary", use_container_width=True):
                if not test_symbols:
                    st.error("❌ Please select at least one symbol to test")
                elif not symbol_strategy_pairs:
                    st.error("❌ Please select at least one strategy to test")
                else:
                    # 生成任务ID
                    task_id = f"custom_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    # 构建命令：传递所有 symbol-strategy pairs
                    # 格式：--symbols sym1 sym2 ... --strategies strat1 strat2 ...
                    symbols_list = [p['symbol'] for p in symbol_strategy_pairs]
                    strategies_list = [p['strategy']['path'] for p in symbol_strategy_pairs]
                    
                    cmd = [
                        sys.executable, "-u",
                        "run_strategy_scanner.py",
                        "--symbols"
                    ] + symbols_list + [
                        "--start", str(scan_start),
                        "--end", str(scan_end),
                        "--strategies"
                    ] + strategies_list
                    
                    # 创建后台任务
                    task = BackgroundTask(
                        task_id=task_id,
                        task_name=f"Custom scan: {len(unique_symbols)} symbols × {len(unique_strategies)} strategies = {len(symbol_strategy_pairs)} tests",
                        cmd=cmd
                    )
                    task.start()
                    
                    st.session_state.tasks[task_id] = task
                    
                    st.success(f"✅ Custom scan started! Task ID: {task_id}")
                    st.info("💡 Scroll down to view the task in the task list with real-time logs. You can also switch to other tabs, the task will continue running in the background.")
                    
                    # 自动滚动到任务列表
                    time.sleep(0.5)
                    st.rerun()
        
        # 显示自定义扫描任务列表
        st.markdown("---")
        st.markdown("### 📋 Custom Scan Tasks")
        
        custom_scan_tasks = {tid: task for tid, task in st.session_state.tasks.items() 
                            if tid.startswith("custom_scan_")}
        
        if not custom_scan_tasks:
            st.info("No custom scan tasks found. Start a custom scan above to see tasks here.")
        else:
            # 自动刷新选项
            auto_refresh = st.checkbox("🔄 Auto Refresh (every 2 seconds)", value=True, key="custom_scan_auto_refresh")
            
            for task_id, task in list(custom_scan_tasks.items()):
                status_icon = {
                    "running": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "stopped": "⏹️"
                }.get(task.status, "❓")
                
                # 状态颜色映射 - 适配白色主题
                status_colors = {
                    "running": "#6366F1",  # 紫色，符合主题
                    "completed": "#10B981",  # 绿色，表示成功
                    "failed": "#EF4444",  # 红色，表示失败
                    "stopped": "#6B7280"  # 灰色，表示停止
                }
                status_color = status_colors.get(task.status, "#1F2937")
                
                with st.expander(
                    f"{status_icon} {task.task_name} | {task.status.upper()} | Duration: {task.get_duration():.1f}s",
                    expanded=(task.status == "running")
                ):
                    # 紧凑布局 - 使用表格形式
                    info_col1, info_col2, info_col3 = st.columns([2.5, 2.5, 1])
                    
                    with info_col1:
                        st.markdown(f"**Task ID:** `{task_id}`<br>**Status:** <span style='color: {status_color}; font-weight: 600; padding: 0.2rem 0.5rem; background: {status_color}15; border-radius: 4px;'>{task.status.upper()}</span>", unsafe_allow_html=True)
                    
                    with info_col2:
                        end_time_str = task.end_time.strftime('%Y-%m-%d %H:%M:%S') if task.end_time else "—"
                        st.markdown(f"**Start:** {task.start_time.strftime('%Y-%m-%d %H:%M:%S')}<br>**End:** {end_time_str}<br>**Duration:** {task.get_duration():.1f}s", unsafe_allow_html=True)
                    
                    with info_col3:
                        if task.status == "running":
                            if st.button("⏹️ Stop", key=f"stop_custom_{task_id}", use_container_width=True):
                                task.stop()
                                st.rerun()
                        else:
                            if st.button("🗑️ Delete", key=f"del_custom_{task_id}", use_container_width=True):
                                del st.session_state.tasks[task_id]
                                st.rerun()
                    
                    # 实时日志 - 使用 checkbox 控制显示，避免自动刷新时关闭
                    if task.status != "completed":
                        logs = task.get_logs()
                        if logs:
                            display_logs = logs[-50:] if len(logs) > 50 else logs
                            log_text = "\n".join(display_logs)
                            
                            # 使用 session_state 保存显示状态
                            log_show_key = f"custom_log_show_{task_id}"
                            if log_show_key not in st.session_state:
                                st.session_state[log_show_key] = False
                            
                            # 使用 checkbox 控制显示
                            show_logs = st.checkbox(
                                f"📜 Logs ({len(display_logs)}/{len(logs)})",
                                value=st.session_state[log_show_key],
                                key=f"custom_log_checkbox_{task_id}",
                                help="Click to show/hide logs"
                            )
                            st.session_state[log_show_key] = show_logs
                            
                            if show_logs:
                                col1, col2 = st.columns([4, 1])
                                with col1:
                                    st.caption(f"Showing last {len(display_logs)} entries")
                                with col2:
                                    if len(logs) > 50:
                                        full_log_text = "\n".join(logs)
                                        st.download_button(
                                            "📥 Download",
                                            data=full_log_text,
                                            file_name=f"{task_id}_logs.txt",
                                            mime="text/plain",
                                            key=f"custom_save_logs_{task_id}",
                                            use_container_width=True
                                        )
                                
                                # 使用纯文本显示，外部加边框
                                log_html = f"""
                                <div style="
                                    border: 1px solid rgba(0, 0, 0, 0.1);
                                    border-radius: 8px;
                                    padding: 1rem;
                                    background: #FFFFFF;
                                    font-family: 'Courier New', monospace;
                                    font-size: 13px;
                                    line-height: 1.6;
                                    color: #1F2937;
                                    max-height: 500px;
                                    overflow-y: auto;
                                    white-space: pre-wrap;
                                    word-wrap: break-word;
                                ">
{log_text}
                                </div>
                                """
                                st.markdown(log_html, unsafe_allow_html=True)
                    
                    # 如果任务完成，显示生成的报告
                    if task.status == "completed":
                        st.markdown("---")
                        
                        # 从日志中提取关键指标
                        logs = task.get_logs()
                        summary_metrics = {}
                        for log in logs:
                            # 查找类似 "BABA: 收益 +177.45%, 夏普 1.54, 胜率 66.7%" 的日志
                            if "收益" in log and "夏普" in log and "胜率" in log:
                                # 提取指标
                                import re
                                match = re.search(r'收益\s+([+-]?\d+\.?\d*)%.*夏普\s+(\d+\.?\d*).*胜率\s+(\d+\.?\d*)%', log)
                                if match:
                                    summary_metrics = {
                                        'return': float(match.group(1)),
                                        'sharpe': float(match.group(2)),
                                        'win_rate': float(match.group(3))
                                    }
                                    break
                        
                        # 显示关键指标卡片
                        if summary_metrics:
                            st.markdown("**📈 Performance Summary:**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                return_color = "normal" if summary_metrics['return'] >= 0 else "off"
                                st.metric("Total Return", f"{summary_metrics['return']:+.2f}%", delta_color=return_color)
                            with col2:
                                st.metric("Sharpe Ratio", f"{summary_metrics['sharpe']:.2f}")
                            with col3:
                                st.metric("Win Rate", f"{summary_metrics['win_rate']:.1f}%")
                            st.markdown("---")
                        
                        st.markdown("**📊 Generated Reports:**")
                        
                        # 检查报告文件
                        report_html = Path("report_assets/scan_report.html")
                        report_csv = Path("report_assets/scan_results.csv")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if report_html.exists():
                                st.success("✅ HTML Report Generated")
                                with open(report_html, 'r', encoding='utf-8') as f:
                                    html_content = f.read()
                                    st.download_button(
                                        "📥 Download HTML Report",
                                        data=html_content,
                                        file_name=f"custom_scan_report_{task_id}.html",
                                        mime="text/html",
                                        key=f"download_html_{task_id}"
                                    )
                                
                                # 显示报告预览按钮
                                if st.button("👁️ Preview Report", key=f"preview_report_{task_id}"):
                                    st.session_state[f"show_report_{task_id}"] = True
                            else:
                                st.warning("⚠️ HTML report not found")
                        
                        with col2:
                            if report_csv.exists():
                                st.success("✅ CSV Results Generated")
                                with open(report_csv, 'r', encoding='utf-8') as f:
                                    csv_content = f.read()
                                    st.download_button(
                                        "📥 Download CSV Results",
                                        data=csv_content,
                                        file_name=f"custom_scan_results_{task_id}.csv",
                                        mime="text/csv",
                                        key=f"download_csv_{task_id}"
                                    )
                                
                                # 显示 CSV 预览
                                try:
                                    df = pd.read_csv(report_csv)
                                    st.table(df)
                                except:
                                    pass
                            else:
                                st.warning("⚠️ CSV results not found")
                        
                        # 显示报告预览
                        if st.session_state.get(f"show_report_{task_id}", False):
                            st.markdown("---")
                            st.markdown("**📈 Report Preview:**")
                            
                            # 查找所有相关的图表文件
                            report_dir = Path("report_assets")
                            
                            # 从 HTML 报告中提取最新的图表文件名
                            latest_charts = {
                                'equity': [],
                                'comparison': None,
                                'details': None
                            }
                            
                            if report_html.exists():
                                try:
                                    with open(report_html, 'r', encoding='utf-8') as f:
                                        html_content = f.read()
                                        
                                        # 提取图片文件名
                                        import re
                                        
                                        # 查找权益曲线图
                                        equity_matches = re.findall(r'scan_equity_[^"]+\.png', html_content)
                                        latest_charts['equity'] = list(set(equity_matches))
                                        
                                        # 查找对比图
                                        comparison_match = re.search(r'scan_comparison_[^"]+\.png', html_content)
                                        if comparison_match:
                                            latest_charts['comparison'] = comparison_match.group(0)
                                        
                                        # 查找详细分析图
                                        details_match = re.search(r'scan_details_[^"]+\.png', html_content)
                                        if details_match:
                                            latest_charts['details'] = details_match.group(0)
                                except Exception as e:
                                    st.warning(f"Could not parse HTML report: {e}")
                            
                            # 显示权益曲线图
                            if latest_charts['equity']:
                                st.markdown("### 📈 Equity Curves")
                                for chart_name in sorted(latest_charts['equity']):
                                    chart_path = report_dir / chart_name
                                    if chart_path.exists():
                                        # 从文件名提取标的符号
                                        symbol = chart_name.split('_')[2]
                                        st.markdown(f"**{symbol}**")
                                        st.image(str(chart_path), use_container_width=True)
                            
                            # 显示对比图表
                            if latest_charts['comparison']:
                                comparison_path = report_dir / latest_charts['comparison']
                                if comparison_path.exists():
                                    st.markdown("### 📊 Performance Comparison")
                                    st.image(str(comparison_path), use_container_width=True)
                            
                            # 显示详细分析图表
                            if latest_charts['details']:
                                details_path = report_dir / latest_charts['details']
                                if details_path.exists():
                                    st.markdown("### 📈 Strategy Details Analysis")
                                    st.image(str(details_path), use_container_width=True)
                            
                            # 显示数据表格
                            if report_csv.exists():
                                st.markdown("### 📋 Scan Results")
                                df = pd.read_csv(report_csv)
                                st.table(df)
                            
                            # 显示交易详情表格（使用 iframe 渲染）
                            if report_html.exists():
                                try:
                                    with open(report_html, 'r', encoding='utf-8') as f:
                                        html_content = f.read()
                                        
                                        # 检查是否有交易详情表格
                                        if "Trade Details" in html_content:
                                            st.markdown("### 📝 Trade Details")
                                            
                                            # 提取所有交易详情表格
                                            import re
                                            
                                            # 找到所有交易详情部分（包含完整的表格）
                                            trade_sections = re.findall(
                                                r'<div class="section">\s*<h2>📝 Trade Details - (.*?)</h2>\s*<table class="data-table">(.*?)</table>\s*</div>',
                                                html_content,
                                                re.DOTALL
                                            )
                                            
                                            if trade_sections:
                                                # 构建完整的 HTML（包含样式）
                                                full_html = """
                                                <!DOCTYPE html>
                                                <html>
                                                <head>
                                                    <meta charset="UTF-8">
                                                    <style>
                                                        body {
                                                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                                            margin: 0;
                                                            padding: 20px;
                                                            background: white;
                                                        }
                                                        .section {
                                                            margin: 30px 0;
                                                        }
                                                        h3 {
                                                            color: #2d3748;
                                                            margin-bottom: 15px;
                                                            font-size: 18px;
                                                            border-bottom: 2px solid #667eea;
                                                            padding-bottom: 8px;
                                                        }
                                                        .data-table {
                                                            width: 100%;
                                                            border-collapse: collapse;
                                                            font-size: 13px;
                                                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                                        }
                                                        .data-table thead {
                                                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                                        }
                                                        .data-table th {
                                                            color: white;
                                                            padding: 12px 8px;
                                                            text-align: center;
                                                            font-weight: bold;
                                                            border: 1px solid #5a67d8;
                                                        }
                                                        .data-table td {
                                                            padding: 10px 8px;
                                                            border: 1px solid #e5e7eb;
                                                            text-align: center;
                                                        }
                                                        .data-table tbody tr:nth-child(odd) {
                                                            background-color: #f9fafb;
                                                        }
                                                        .data-table tbody tr:hover {
                                                            background-color: #e5e7eb;
                                                        }
                                                        .positive {
                                                            color: #10b981;
                                                            font-weight: bold;
                                                        }
                                                        .negative {
                                                            color: #ef4444;
                                                            font-weight: bold;
                                                        }
                                                    </style>
                                                </head>
                                                <body>
                                                """
                                                
                                                for symbol_name, table_content in trade_sections:
                                                    full_html += f"""
                                                    <div class="section">
                                                        <h3>{symbol_name}</h3>
                                                        <table class="data-table">
                                                            {table_content}
                                                        </table>
                                                    </div>
                                                    """
                                                
                                                full_html += """
                                                </body>
                                                </html>
                                                """
                                                
                                                # 使用 components 渲染
                                                st.components.v1.html(full_html, height=600, scrolling=True)
                                            else:
                                                st.info("No trade details table found in report")
                                except Exception as e:
                                    st.error(f"Could not extract trade details: {e}")
                                    import traceback
                                    st.code(traceback.format_exc())
                            
                            if st.button("❌ Close Preview", key=f"close_preview_{task_id}"):
                                st.session_state[f"show_report_{task_id}"] = False
                                st.rerun()
            
            # 自动刷新逻辑
            if auto_refresh:
                # 检查是否有运行中的任务
                has_running = any(task.status == "running" for task in custom_scan_tasks.values())
                if has_running:
                    time.sleep(2)
                    st.rerun()


# ==================== Results View ====================
if __name__ == "__main__":
    pass  # Streamlit handles the execution


# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>Quantitative Trading Strategy Platform v1.0 | Powered by Streamlit</p>
    <p>© 2025 All Rights Reserved</p>
</div>
""", unsafe_allow_html=True)

