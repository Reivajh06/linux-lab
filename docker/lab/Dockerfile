FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive LANG=en_US.UTF-8 DISPLAY=:1
# Ubuntu's minimal image excludes manuals by default; restore them before install.
RUN rm -f /etc/dpkg/dpkg.cfg.d/excludes && \
    apt-get update && apt-get install -y --no-install-recommends \
    locales sudo bash bash-completion coreutils util-linux passwd login adduser \
    vim vim-tiny nano gedit man-db manpages manpages-dev info less \
    findutils grep sed gawk diffutils file tree tar gzip bzip2 xz-utils zip unzip \
    procps psmisc iproute2 iputils-ping dnsutils curl wget netcat-openbsd \
    python3 python3-venv ca-certificates openssh-client rsync acl \
    openbox xfce4-terminal tigervnc-standalone-server tigervnc-common \
    websockify dbus-x11 x11-xserver-utils x11-utils fonts-dejavu supervisor \
    poppler-utils tesseract-ocr tesseract-ocr-eng tesseract-ocr-spa && \
    apt-get install -y --reinstall coreutils bash util-linux findutils grep sed tar gzip && \
    locale-gen en_US.UTF-8 && mandb && rm -rf /var/lib/apt/lists/* && \
    useradd -m -s /bin/bash learner && \
    printf 'learner ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/learner && chmod 0440 /etc/sudoers.d/learner && \
    install -d -o learner -g learner /home/learner/.config/openbox && \
    printf '\nexport DISPLAY=:1\nexport LANG=en_US.UTF-8\n' >> /home/learner/.bashrc
RUN if [ -f /usr/bin/man.REAL ]; then rm -f /usr/bin/man && dpkg-divert --quiet --divert /usr/bin/man.REAL --rename --remove /usr/bin/man; fi
COPY install-browser.sh /opt/linux-lab-workspace/install-browser.sh
RUN bash /opt/linux-lab-workspace/install-browser.sh
COPY workspace.py /opt/linux-lab-workspace/workspace.py
COPY lab-terminal /usr/local/bin/lab-terminal
COPY desktop.sh /usr/local/bin/lab-desktop
COPY supervisord.conf /etc/supervisor/conf.d/lab.conf
COPY welcome.txt /etc/motd
RUN chmod +x /usr/local/bin/lab-desktop /usr/local/bin/lab-terminal && \
    install -d -o learner -g learner /home/learner/.config /home/learner/.config/openbox \
    /home/learner/.config/xfce4 /home/learner/.config/xfce4/terminal /home/learner/.config/gtk-3.0
EXPOSE 6080
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
