"""Offline Node preparation for installer tests of unrelated host/runtime seams."""

from unittest.mock import patch

from scripts import orchflows_node


def offline_node_preparation():
    """Keep lock validation and stamps real; replace only external tooling."""

    ensure = orchflows_node.ensure

    def prepare(kind, name, item_dir):
        return ensure(kind, name, item_dir, which=lambda name: name,
                      installer=lambda path, command: None)

    return patch.object(orchflows_node, "ensure", side_effect=prepare)
