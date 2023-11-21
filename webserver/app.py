#!/usr/bin/env python3
from aws_cdk import (

    App,
    Aws,
    Environment

)
from webserver.webserver_stack import WebserverStack

app = App()
env = app.node.try_get_context("env")
context = app.node.try_get_context(env)
account = context['account_id']
region = context['region']
aws_env = Environment(account=account,region=region)
WebserverStack(app, "WebserverStack",env=aws_env)

app.synth()
