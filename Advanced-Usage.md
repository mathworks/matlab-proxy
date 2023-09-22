# Advanced Usage
Copyright (c) 2020-2023 The MathWorks, Inc. All rights reserved.

This page lists some of the advanced manuevers that may be of specific interest to help configure the package for use in your environment.

## Environment Variables

To control the behavior of the MATLAB Proxy, you can optionally specify the environment variables described in this section. You must specify these variables before starting the integration. For example, a network license server can be specified when you start the integration using the command below:

```bash
env MLM_LICENSE_FILE="1234@example.com" matlab-proxy-app
```

The following table describes all the environment variables that you can set to customize the behavior of this integration.

| Name | Type | Example Value | Description |
| ---- | ---- | ------------- | ----------- |
| **MLM_LICENSE_FILE** | string | `"1234@111.22.333.444"` | When you want to use either a license file or a network license manager to license MATLAB, specify this variable.</br> For example, specify the location of the network license manager to be `123@hostname`.|                                                                         
| **MWI_BASE_URL** | string | `"/matlab"` | Set to control the base URL of the app. MWI_BASE_URL should start with `/` or be `empty`. |
| **MWI_APP_PORT** | integer | `8080` | Specify the port for the HTTP server to listen on. |
| **MWI_APP_HOST** | string | `127.0.0.1` | Specify the host interface for the HTTP server to launch on. Defaults to `0.0.0.0` on POSIX and Windows systems.<br />With the default value, the server will be accessible remotely at the fully qualified domain name of the system. |
| **MWI_LOG_LEVEL** | string | `"CRITICAL"` | Specify the Python log level to be one of the following `NOTSET`, `DEBUG`, `INFO`, `WARN`, `ERROR`, or `CRITICAL`. For more information on Python log levels, see [Logging Levels](https://docs.python.org/3/library/logging.html#logging-levels) .<br />The default value is `INFO`. |
| **MWI_LOG_FILE** | string | `"/tmp/logs.txt"` | Specify the full path to the file where you want debug logs from this integration to be written. |
| **MWI_ENABLE_WEB_LOGGING** | string | `"True"` | Set this value to `"True"` to see additional web server logs. |
| **MWI_CUSTOM_HTTP_HEADERS** | string  |`'{"Content-Security-Policy": "frame-ancestors *.example.com:*"}'`<br /> OR <br />`"/path/to/your/custom/http-headers.json"` |Specify valid HTTP headers as JSON data in a string format. <br /> Alternatively, specify the full path to the JSON file containing valid HTTP headers instead. These headers are injected into the HTTP response sent to the browser. </br> For  more information, see the [Custom HTTP Headers](#custom-http-headers) section.|
| **TMPDIR** or **TMP** | string | `"/path/for/MATLAB/to/use/as/tmp"` | Set either one of these variables to control the temporary folder used by MATLAB. `TMPDIR` takes precedence over `TMP` and if neither variable is set, `/tmp` is the default value used by MATLAB. |
| **MWI_SSL_CERT_FILE** | string | `"/path/to/certificate.pem"` | The certfile string must be the path to a single file in PEM format containing the certificate as well as any number of CA certificates needed to establish the certificate’s authenticity. See [SSL Support](./SECURITY.md#ssl-support) for more information.|
| **MWI_SSL_KEY_FILE** | string | `"/path/to/keyfile.key"` | The keyfile string, if present, must point to a file containing the private key. Otherwise the private key will be taken from certfile as well. |
| **MWI_ENABLE_TOKEN_AUTH** | string | `"True"` | When set to `True`, matlab-proxy will require users to provide the security token to access the proxy. One can optionally set the token using the environment variable `MWI_AUTH_TOKEN`. If `MWI_AUTH_TOKEN` is not specified, then a token will be generated for you. <br />The default value is `False` . See [Token-Based Authentication](./SECURITY.md#token-based-authentication) for more information.|
| **MWI_AUTH_TOKEN** | string (optional) | `"AnyURLSafeToken"` | Specify a custom `token` for matlab-proxy to use with [Token-Based Authentication](./SECURITY.md#token-based-authentication). A token can safely contain any combination of alpha numeric text along with the following permitted characters: `- .  _  ~`.<br />When absent matlab-proxy will generate a random URL safe token. |
| **MWI_USE_EXISTING_LICENSE** | string (optional) | `"True"` | When set to True, matlab-proxy will not ask you for additional licensing information and will try to launch an already activated MATLAB on your system PATH.
| **MWI_CUSTOM_MATLAB_ROOT** | string (optional) | `"/path/to/matlab/root/"` | Optionally, provide a custom path to MATLAB root. For more information see [Adding MATLAB to System Path](#adding-matlab-to-system-path) |

## Adding MATLAB to System Path

When `matlab-proxy` starts, it expects the `matlab` executable to be present on  system PATH in the environment from which it was spawned.

`matlab-proxy` will error out if it is unable to find `matlab` on the PATH.

One can add it to the system PATH using the following commands:
```bash
# On Linux & MacOS
sudo ln -fs ${MATLAB_ROOT}/bin/matlab /usr/bin/matlab

# On Windows environments
setx PATH "${MATLAB_ROOT}\bin;%PATH%"
```
Where `MATLAB_ROOT` points to the folder in which MATLAB was installed.
Example values of `MATLAB_ROOT` on various platforms are:
```
On linux: /usr/local/MATLAB/R2023a
On MacOS: /Applications/MATLAB_R2023a.app
On Windows: C:\Program Files\MATLAB\R2023a
```

### Custom MATLAB Root

Use the environment variable `MWI_CUSTOM_MATLAB_ROOT` to specify the location of `MATLAB_ROOT`.

When this environment variable is set, `matlab-proxy` will not search the system PATH for MATLAB.

This might be useful in the following situations:

1. Changes to the system PATH are not possible or desirable.
2. There are multiple MATLAB installations on a system, and you want to use `matlab-proxy` with a particular installation of MATLAB.
3. The existing `matlab` executable on PATH is a user defined script as explained in this [issue](https://github.com/mathworks/matlab-proxy/issues/3).

Example usage:
```bash
env MWI_CUSTOM_MATLAB_ROOT=/opt/software/matlab/r2023a matlab-proxy-app
```



## Custom HTTP Headers 
If the web browser renders the MATLAB Proxy with some other content, then the browser could block the integration because of mismatch of `Content-Security-Policy` header in the response headers from the integration.
To avoid this, provide custom HTTP headers. This allows browsers to load the content.

For example, if this integration is rendered along with some other content on the domain `www.example.com`, to allow the browser to load the content, create a JSON file of the following form:

```json
{
  "Content-Security-Policy": "frame-ancestors *.example.com:* https://www.example.com:*;"
}
```
Specify the full path to this sample file in the environment variable `MWI_CUSTOM_HTTP_HEADERS`.
Alternatively, if you want to specify the custom HTTP headers as a string in the environment variable, in a bash shell type a command of the form below:

```bash
export MWI_CUSTOM_HTTP_HEADERS='{"Content-Security-Policy": "frame-ancestors *.example.com:* https://www.example.com:*;"}'
```

If you add the `frame-ancestors` directive, the browser does not block the content of this integration hosted on the domain `www.example.com`.


For more information about `Content-Security-Policy` header,  check the [Mozilla developer docs for Content-Security-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy).

**NOTE**: Setting custom HTTP headers is an advanced operation, only use this functionality if you are familiar with HTTP headers.
