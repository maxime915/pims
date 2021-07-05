FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

RUN apt-get -y update && apt-get -y install --no-install-recommends --no-install-suggests \
        `# Essentials` \
        automake \
        build-essential \
        ca-certificates \
        gcc \
        net-tools \
        wget \
        software-properties-common \
        `# Vips dependencies` \
        pkg-config \
        glib2.0-dev \
        libexpat1-dev \
        libtiff5-dev \
        libjpeg62-turbo-dev \
        libgsf-1-dev \
        libexif-dev \
        orc-0.4-dev \
        libwebp-dev \
        liblcms2-dev \
        libpng-dev \
        gobject-introspection \
        `# Openslide dependencies` \
        libcairo2-dev \
        libgdk-pixbuf2.0-dev \
        libopenjp2-7-dev \
        libxml2-dev \
        libsqlite3-dev \
        libtool \
        `# Other tools` \
        libimage-exiftool-perl && \
    rm -rf /var/lib/apt/lists/*

# openslide
ARG OPENSLIDE_VERSION=3.4.1
RUN cd /tmp && \
    wget https://github.com/openslide/openslide/releases/download/v${OPENSLIDE_VERSION}/openslide-${OPENSLIDE_VERSION}.tar.gz && \
    tar -zxvf ./openslide-${OPENSLIDE_VERSION}.tar.gz && \
    cd ./openslide-${OPENSLIDE_VERSION} && \
    autoreconf -i && \
    ./configure && \
    make && \
    make install && \
    ldconfig

# vips
ARG VIPS_VERSION=8.10.6
RUN cd /tmp && \
    wget https://github.com/libvips/libvips/releases/download/v${VIPS_VERSION}/vips-${VIPS_VERSION}.tar.gz && \
    tar -zxvf ./vips-${VIPS_VERSION}.tar.gz && \
    cd ./vips-${VIPS_VERSION} && \
    LDFLAGS="-L/usr/local/lib -lopenslide" CPPFLAGS="-I/usr/local/include/openslide" ./configure && \
    make && \
    make install && \
    ldconfig

WORKDIR /app

# Install python requirements
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Prestart configuration
RUN touch /tmp/addHosts.sh
COPY ./docker/prestart.sh /app/prestart.sh
RUN chmod +x /app/prestart.sh

# Add default config
COPY ./pims-config.env /app/pims-config.env
COPY ./logging-prod.yml /app/logging-prod.yml
COPY ./docker/gunicorn_conf.py /app/gunicorn_conf.py

# Add app
COPY ./pims /app/pims
ENV MODULE_NAME="pims.application"

ENV PORT=5000
EXPOSE ${PORT}
