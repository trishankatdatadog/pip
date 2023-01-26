import "list"

// https://github.com/theupdateframework/taps/blob/master/tap4.md

// Every PyPI-like index must be served over HTTPS.
// https://cuelang.org/docs/tutorials/tour/types/stringraw/
#URL: =~ #"^(https://).+$"#
#Repository: {
	// Repository name: List of URLs
	[string]: [...#URL]
}
repositories: {
	#Repository
}
// The list of available #Repository names.
// https://github.com/cue-lang/cue/discussions/715#discussioncomment-960093
#Repositories: or([for name, _ in repositories {name}])

// Every character in #Path must be a Perl word character, "/", or "*".
// TODO: refine syntax.
#Path: =~ #"^[\w/\*]+$"#
#Mapping: {
	// The set of target path patterns that must be matched to these repositories.
	paths: [...#Path] & list.UniqueItems

	// The subset of repositories that must provide metadata about the targets
	// matching the paths specified above.
    repositories: [...#Repositories] & list.UniqueItems

	// The threshold is the number of repositories specified above that must
	// agree on metadata about targets that match the paths specified above.
	// This number must be in [1, # of repositories].
	// By default, it "errs" on the safe side (the upper bound).
	threshold: >=1 & <=len(repositories) | *len(repositories)

	// Should we terminate the search right here and now if this matching
	// mapping fails to yield the target?
	// By default, it "errs" on the safe side (yes).
	terminating: bool | *true
}
mapping: [...#Mapping]
