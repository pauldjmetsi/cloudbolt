"""
This is a working sample CloudBolt plug-in for you to start with. The run method is required,
but you can change all the code within it. See the "CloudBolt Plug-ins" section of the docs for
more info and the CloudBolt forge for more examples:
https://github.com/CloudBoltSoftware/cloudbolt-forge/tree/master/actions/cloudbolt_plugins
"""
from common.methods import set_progress


def run(job, server=None, resource=None, *args, **kwargs):
    ip = server.ip
    url = f"http://{ip}:5601"
    resource.elastic_url = url
    resource.save()
    server.elastic_url = url 
    server.save()
    return "", "", ""