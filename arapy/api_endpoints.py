#api_endpoints.py

"""
ClearPass 6.11.13 API endpoints
"""

API_ENDPOINTS = {
    # ----API Operations
    "oauth": "/api/oauth",
    "oauth-me": "/api/oauth/me",
    "oauth-privileges": "/api/oauth/privileges",

    # ----Certificate Authority
    "certificate": "/api/certificate",
    "certificate-chain": "/api/certificate/{cert_id}/chain",
    "certificate-export": "/api/certificate/{cert_id}/export",
    "certificate-import": "/api/certificate/import",
    "certificate-new": "/api/certificate/new",
    "certiticate-reject": "/api/certificate/{cert_id}/reject",
    "certificate-request" : "/api/certificate/request",
    "certificate-revoke": "/api/certificate/{cert_id}/revoke",
    "certificate-sign-request": "/api/certificate/{cert_id}/sign",
    "onboard-debice" : "/api/onboard/device",
    "onboard-user": "/api/user",

    #----Guest Actions
    "generate-guest-digital-pass": "/api/guest/{guest_id}/pass/{id}",
    "genereate-guest-receipt": "/api/guest/{guest_id}/receipt/{id}",
    "send-sms-receipt": "/api/guest/{guest_id}/sendreceipt/sms",
    "send-snmp-receipt": "/api/guest/{guest_id}/sendreceipt/smtp",
    "sponsorship-approval": "/api/guest/{guest_id}/sponsor",

    #----Guest Configuration
    "digital-pass-template": "/api/template/pass",
    "guest-authentication-configuration": "/api/guest/authentication",
    "guest-manager": "/api/guestmanager",
    "print-template": "/api/template/print",
    "web-login": "/api/weblogin",

    #----Tools and Utilities
    "email-send": "/api/email/send",
    "random-mpsk-generator": "/api/random-mpsk",
    "random-password-generator": "/api/random-password",
    "send-sms": "/api/sms/send",

    #----Platform Certificates
    "cert-sign-request": "/api/cert-sign-request",
    "cert-trust-list": "/api/cert-trust-list",
    "cert-trust-list-details": "/api/cert-trust-list-details",
    "client-cert": "/api/client-cert",
    "revocation-list": "/api/revocation-list",
    "self-signed-cert": "/api/self-signed-cert",
    "server-cert": "/api/server-cert",
    "service-cert": "/api/service-cert",

    #----Identities
    "api-client": "/api/api-client",
    "deny-listed-users": "/api/deny-listed-users",
    "device": "/api/device",
    "endpoint": "/api/endpoint",
    "external-account": "/api/external-account",
    "guest-user": "/api/guest-user",
    "local-user": "/api/local-user",
    "static-host-list": "/api/static-host-list",

    #----Logs
    "endpoint-info": "/api/insight/endpoint/mac",
    "login-audit": "/api/login-audit",
    "system-event": "/api/system-event",

    #----Local Server Configuration
    "ad-domain": "/api/ad-domain",
    "access-control": "/api/server/access-control",
    "cppm-version": "/api/cppm-version",
    "server-configuration": "/api/cluster/server",
    "server-fips": "/api/server/fips",
    "server-snmp": "/api/server/snmp",
    "server-version": "/api/server/version",
    "service-parameter": "/api/service-parameter",
    "system-service-control": "/api/server/service",

    #----Global Server Configuration
    "admin-privilege": "/api/admin-privilege",
    "admin-user": "/api/admin-user",
    "admin-user-password-policy": "/api/admin-user/password-policy",
    "application-license": "/api/application-license",
    "attribute": "/api/attribute",
    "clearpass-portal": "/api/clearpass-portal",
    "cluster-db-sync": "/api/cluster/db-sync",
    "cluster-wide-parameters": "/api/cluster/parameters",
    "data-filter": "/api/data-filter",
    "file-backup-server": "/api/file-backup-server",
    "list-all-privileges": "/api/oauth/all-privileges",
    "local-user-password-policy": "/api/local-user/password-policy",
    "essaging-setup": "/api/messaging-setup",
    "operator-profile": "/api/operator-profile",
    "policy-manager-zone": "/api/server/policy-manager-zones",
    "snmp-trap-receiver": "/api/snmp-trap-receiver",

    #----Integrations
    "context-server-action": "/api/context-server-action",
    "device-insight": "/api/device-insight",
    "endpoint-context-server": "/api/endpoint-context-server",
    "event-source": "/api/event-sources",
    "extension-instance": "/api/extension/instance",
    "extension-instance-config": "/api/extension/instance/{id}/config",
    "extension-instance-log": "/api/extension/instance/{id}/log",
    "extension-instance-reinstall": "/api/extension/instance/{id}/reinstall",
    "extension-instance-restart": "/api/extension/instance/{id}/restart",
    "extension-instance-start": "/api/extension/instance/{id}/start",
    "extension-instance-stop": "/api/extension/instance/{id}/stop",
    "extension-instance-upgrade": "/api/extension/instance/{id}/upgrade",
    "extension-store": "/api/extension/store",
    "ingress-event-dictionary": "/api/ingress-event-dictionary",
    "syslog-export-filter": "/api/syslog-export-filter",
    "syslog-target": "/api/syslog-target",

    # ----Policy Elements
    "application-dictionary": "/api/application-dictionary",
    "auth-method": "/api/auth-method",
    "auth-source": "/api/auth-source",
    "enforcement-policy": "/api/enforcement-policy",
    "network-device": "/api/network-device",
    "network-device-group": "/api/network-device-group",
    "posture-policy": "/api/posture-policy",
    "radius-dictionary": "/api/radius-dictionary",
    "radius-dynamic-authorization-template": "/api/radius-dynamic-authorization-template",
    "radius-proxy-target": "/api/proxy-target",
    "role": "/api/role",
    "role-mapping": "/api/role-mapping",
    "service": "/api/service",
    "tacacs-service-dictionary": "/api/tacacs-service-dictionary",

    #----Endpoint Visibility
    "agentless-onguard-settings": "/api/agentless-onguard/settings",
    "agentless-onguard-subnet-mapping": "/api/agentless-onguard/subnet-mapping",
    "device-fingerprint": "/api/device-profiler/device-fingerprint",
    "fingerprint-dictionary": "/api/fingerprint",
    "network-scan": "/api/config/network-scan",
    "onguard-activity": "api/onguard-activity",
    "onguard-custom-script": "/api/onguard-custom-script",
    "onguard-global-settings": "/api/onguard/global-settings",
    "onguard-settings": "/api/onguard/settings",
    "onguard-zone-mapping": "/api/onguard/policy-manager-zones",
    "profiler-subnet-mapping": "/api/profiler-subnet-mapping",
    "windows-hotfix": "/api/windows-hotfix",

    #----Session Control
    "active-session": "/api/session",
    "active-session-disconnect": "/api/session/{id}/disconnect",
    "active-session-reauthorize": "/api/session/{id}/reauthorize",
    "mac-active-session": "/api/active-session/{mac_address}",
    "session-action": "/api/session-action/disconnect",

    #----Enforcement Profile
    "captive-portal-profile": "/api/enforcement-profile-dur/captive-portal-profile/{product_name}",
    "dur-class": "/api/enforcement-profile-dur/dur-class/{product_name}",
    "enforcement-profile": "/api/enforcement-profile",
    "ethertype-access-control-list": "/api/enforcement-profile-dur/ethertype-access-control-list/{product_name}",
    "mac-access-control-list": "/api/enforcement-profile-dur/mac-access-control-list/{product_name}",
    "nat-pool": "/api/enforcement-profile-dur/nat-pool/{product_name}",
    "net-destination": "/api/enforcement-profile-dur/net-destination/{product_name}",
    "net-service": "/api/enforcement-profile-dur/net-service/{product_name}",
    "policer-profile": "/api/enforcement-profile-dur/policer-profile/{product_name}",
    "policy": "/api/enforcement-profile-dur/policy/{product_name}",
    "qos-profile": "/api/enforcement-profile-dur/qos-profile/{product_name}",
    "session-access-control-list": "/api/enforcement-profile-dur/session-access-control-list/{product_name}",
    "statless-access-control-list": "/api/enforcement-profile-dur/stateless-access-control-list/{product_name}",
    "time-range": "/api/enforcement-profile-dur/time-range/{product_name}",
    "voip-profile": "/api/enforcement-profile-dur/voip-profile/{product_name}",

    #----Insight
    "alert": "/api/alert",
    "report": "/api/report",
}

