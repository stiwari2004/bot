package troubleshooting.supplychain

import data.inventory.signature_trust

default deny = false

deny[msg] {
	input.review.kind.kind == "Pod"
	container := input.review.object.spec.containers[_]
	not image_signed_and_trusted(container.image)
	msg := sprintf("image %s is missing a valid cosign signature", [container.image])
}

image_signed_and_trusted(image) {
	signature := signature_trust[image]
	signature.verified == true
	signature.key_id == input.parameters.trusted_key_id
}

