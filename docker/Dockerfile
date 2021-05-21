FROM python:3.8-buster

RUN apt-get -y update && apt-get -y install --no-install-recommends --no-install-suggests \
        `# Essentials` \
        automake \
        build-essential \
        ca-certificates \
        git \
        gcc \
        locate \
        net-tools \
        unzip \
        wget \
        gawk \
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

# Install python requirements
COPY requirements.txt /app/requirements.txt
WORKDIR /app

COPY pims /app/pims
COPY setup.py /app/setup.py

#COPY deploy.sh /app/deploy.sh
#RUN chmod +x /app/deploy.sh


# TODO: NOT READY FOR PRODUCTION - ONLY FOR DEV.
COPY app-config.cfg /app/app-config.cfg
RUN pip3 install setuptools && python3 setup.py install

RUN pip3 install uwsgi
COPY uwsgi.ini /app/uwsgi.ini

EXPOSE 5000

CMD [ "uwsgi", "--ini", "/app/uwsgi.ini" ]
