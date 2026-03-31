from netloom.cli.completion import completion_candidates


def test_completion_candidates_include_full_only_services():
    candidates = completion_candidates(
        ["certificateauthority", "--_cur="],
        {
            "modules": {
                "certificateauthority": {
                    "certificate": {
                        "actions": {
                            "list": {"method": "GET", "paths": ["/api/certificate"]}
                        }
                    }
                }
            },
            "full_modules": {
                "certificateauthority": {
                    "certificate": {
                        "actions": {
                            "list": {"method": "GET", "paths": ["/api/certificate"]}
                        }
                    },
                    "certificate-chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {},
                    },
                }
            },
        },
    )

    assert "certificate" in candidates
    assert "certificate-chain" in candidates


def test_completion_candidates_do_not_invent_actions_for_summary_only_service():
    candidates = completion_candidates(
        ["certificateauthority", "certificate-chain"],
        {
            "modules": {
                "certificateauthority": {
                    "certificate": {
                        "actions": {
                            "list": {"method": "GET", "paths": ["/api/certificate"]}
                        }
                    }
                }
            },
            "full_modules": {
                "certificateauthority": {
                    "certificate-chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {},
                    }
                }
            },
        },
    )

    assert candidates == []


def test_completion_candidates_hide_short_aliases_when_canonical_services_exist():
    candidates = completion_candidates(
        ["certificateauthority", "--_cur="],
        {
            "modules": {
                "certificateauthority": {
                    "chain": {
                        "actions": {
                            "get": {
                                "method": "GET",
                                "paths": ["/api/certificate/chain/{id}"],
                                "summary": "Get a certificate and its trust chain",
                            }
                        }
                    },
                    "device": {
                        "actions": {
                            "list": {
                                "method": "GET",
                                "paths": ["/api/device"],
                                "summary": "Get a list of devices",
                            }
                        }
                    },
                }
            },
            "full_modules": {
                "certificateauthority": {
                    "certificate-chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {},
                    },
                    "onboard-device": {
                        "summary": "Manage Onboard devices",
                        "actions": {},
                    },
                }
            },
        },
    )

    assert "certificate-chain" in candidates
    assert "onboard-device" in candidates
    assert "chain" not in candidates
    assert "device" not in candidates


def test_completion_candidates_hide_aliases_when_both_forms_exist_in_full_modules():
    candidates = completion_candidates(
        ["certificateauthority", "--_cur="],
        {
            "modules": {
                "certificateauthority": {
                    "certificate-chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {},
                    },
                    "chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {"get": {"method": "GET"}},
                    },
                }
            },
            "full_modules": {
                "certificateauthority": {
                    "certificate-chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {},
                    },
                    "chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {"get": {"method": "GET"}},
                    },
                }
            },
        },
    )

    assert "certificate-chain" in candidates
    assert "chain" not in candidates


def test_completion_candidates_hide_request_alias_when_summary_picks_one_match():
    candidates = completion_candidates(
        ["certificateauthority", "--_cur="],
        {
            "modules": {
                "certificateauthority": {
                    "request": {
                        "summary": "Import a certificate signing request",
                        "actions": {"add": {"method": "POST"}},
                    }
                }
            },
            "full_modules": {
                "certificateauthority": {
                    "certificate-request": {
                        "summary": "Import a certificate signing request",
                        "actions": {},
                    },
                    "certificate-sign-request": {
                        "summary": "Sign a certificate signing request",
                        "actions": {},
                    },
                    "request": {
                        "summary": "Import a certificate signing request",
                        "actions": {"add": {"method": "POST"}},
                    },
                }
            },
        },
    )

    assert "certificate-request" in candidates
    assert "certificate-sign-request" in candidates
    assert "request" not in candidates
