FROM nginx:1.27-alpine

# Install required tools for building the otel module
RUN apk add --no-cache git build-base pcre-dev zlib-dev openssl-dev curl-dev linux-headers

# Clone the OpenTelemetry NGINX module
RUN git clone --branch v1.1.0 https://github.com/open-telemetry/opentelemetry-cpp-contrib.git /tmp/otel-nginx

# Download NGINX source to build module against same version
RUN wget http://nginx.org/download/nginx-1.27.0.tar.gz && \
    tar -xzf nginx-1.27.0.tar.gz

WORKDIR /nginx-1.27.0

# Build the otel module
RUN ./configure --add-dynamic-module=/tmp/otel-nginx/instrumentation/nginx && make modules

# Copy the built module to nginx modules folder
RUN cp objs/ngx_http_opentelemetry_module.so /etc/nginx/modules/

# Clean up
RUN rm -rf /tmp/otel-nginx nginx-1.27.0*

# Copy configuration
COPY nginx.conf /etc/nginx/nginx.conf

CMD ["nginx", "-g", "daemon off;"]
