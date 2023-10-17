#!/usr/bin/env python3
import os

from aws_cdk import (

    App,
    Aws,
    Environment

)

from project.project_stack import ProjectStack


app = App()
env = app.node.try_get_context("env")
context = app.node.try_get_context(env)
account = context['account_id']
region = context['region']
aws_env = Environment(account=account,region=region)
ProjectStack(app, "ProjectStack",env=aws_env)

app.synth()
