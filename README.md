# VMware script for reverting VM snaphots

## Table of Contents

## Abstract
This document describes the LatecoLotteryServer. 
The server have been developed to work with python 3.3+

## Quick Start Guide

### Installing Required Python Packages
pip install --upgrade extra-lib/vapi_client_bindings-1.3.1-py2.py3-none-any.whl
pip install --upgrade extra-lib/vapi_common_client-2.9.0-py2.py3-none-any.whl
pip install --upgrade extra-lib/vapi_runtime-2.9.0-py2.py3-none-any.whl
pip install --upgrade extra-lib/vapi_vmc_client-2.9.0-py2.py3-none-any.whl
pip install --upgrade extra-lib/vmc_client_bindings-1.2.0-py2.py3-none-any.whl

pip install --upgrade -r requirements.txt


### Run script
python ./vmware-preparation-students.py -s 'server' -u 'username' -p 'password' -students Student01 Student02
 
