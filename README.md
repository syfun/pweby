# pweby

基于python eventlet的web框架，追求简洁，可以通过简单的步骤就可以构建一个web服务。支持jinja2模板。

Note: 这个说明只是很简单的举个2个示例，后面需要详细介绍。

## 安装

代码暂时没有放到pypi上，所以只能通过源码安装

    python setup.py sdist
    cd dist && pip install pweby-0.1.2.zip
    
## 使用

示例代码在pweby/demos中可以看到。

最简单的例子

    #!/usr/bin/env python
    # coding=utf8
    
    import pweby
    
    
    class Hello(pweby.Application):
    
        @pweby.route('/')
        def hello(self, req):
            return pweby.Response('Hello World!')
    
    
    server = pweby.Server(Hello, host='127.0.0.1', port=8080)
    server.serve()
    
使用模板和配置的例子

hello.py

    #!/usr/bin/env python
    # coding=utf8
    
    import pweby
    
    
    CONF = pweby.set_config('pweby.yml')
    
    
    class Hello(pweby.Application):
    
        @pweby.route('/')
        def hello(self, req, template_name='index.html'):
            return pweby.render(template_name, name='world')
    
    
    server = pweby.Server(Hello, host=CONF.host, port=CONF.port)
    server.serve()
    
模板index.html

    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title></title>
    </head>
    <body>
    Hello {{name}}!
    </body>
    </html>
    
配置文件pweby.yml

    # listen host and port
    host: 0.0.0.0
    port: 8080
    
    # templates path
    template_path: ['templates']
