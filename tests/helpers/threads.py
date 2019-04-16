"""
Testing helper functions to modify the threads of the audit node
"""


def replace_thread(audit_node, thread_type, replacement):
    assert not audit_node.exec
    threads = audit_node._QSPAuditNode__internal_threads
    for i, thread in enumerate(threads):
        if type(thread) == thread_type:
            threads[i] = replacement
