FROM fedora:44
LABEL linux-lab.base=fedora
ENV LANG=en_US.UTF-8 DISPLAY=:1
# Fedora's container image skips manuals (tsflags=nodocs); restore them before install.
RUN sed -i '/^tsflags=nodocs/d' /etc/dnf/dnf.conf && \
    dnf reinstall -y --skip-unavailable $(rpm -qa --qf '%{NAME} ') && \
    dnf install -y --setopt=install_weak_deps=False \
    glibc-langpack-en glibc-langpack-es sudo bash bash-completion coreutils util-linux passwd shadow-utils \
    vim-enhanced vim-minimal nano gedit man-db man-pages info less \
    findutils grep sed gawk diffutils file tree tar gzip bzip2 xz zip unzip \
    words bc htop lsof \
    procps-ng psmisc iproute iputils bind-utils curl wget nmap-ncat \
    hostname cronie at net-tools traceroute plocate binutils strace tmux screen git-core jq \
    usbutils pciutils sysstat \
    python3 ca-certificates openssh-clients rsync acl \
    openbox gnome-terminal tigervnc-server-minimal python3-websockify \
    dbus-x11 dbus-daemon xsetroot xprop xdpyinfo wmctrl supervisor \
    dejavu-sans-fonts dejavu-sans-mono-fonts adwaita-mono-fonts adwaita-sans-fonts \
    adwaita-icon-theme glib2 dconf gsettings-desktop-schemas \
    poppler-utils tesseract tesseract-langpack-eng tesseract-langpack-spa firefox && \
    mandb -q && dnf clean all && rm -rf /var/cache/dnf /var/cache/libdnf5 && \
    useradd -m -s /bin/bash learner && \
    printf 'learner ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/learner && chmod 0440 /etc/sudoers.d/learner && \
    install -d -o learner -g learner /home/learner/.config/openbox && \
    printf '\nexport DISPLAY=:1\nexport LANG=en_US.UTF-8\n' >> /home/learner/.bashrc
COPY install-browser.sh /opt/linux-lab-workspace/install-browser.sh
RUN sed -i 's/\r$//' /opt/linux-lab-workspace/install-browser.sh && bash /opt/linux-lab-workspace/install-browser.sh
COPY workspace.py /opt/linux-lab-workspace/workspace.py
COPY lab-terminal /usr/local/bin/lab-terminal
COPY desktop.sh /usr/local/bin/lab-desktop
COPY supervisord.conf /etc/supervisord.conf
COPY welcome.txt /etc/motd
RUN sed -i 's/\r$//' /usr/local/bin/lab-desktop /usr/local/bin/lab-terminal /etc/supervisord.conf && \
    chmod +x /usr/local/bin/lab-desktop /usr/local/bin/lab-terminal && \
    install -d -o learner -g learner /home/learner/.config /home/learner/.config/openbox \
    /home/learner/.config/gtk-3.0
EXPOSE 6080
CMD ["supervisord", "-n", "-c", "/etc/supervisord.conf"]
