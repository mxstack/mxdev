##############################################################################
# Custom Makefile targets
# This file is included by the mxmake-generated Makefile and will be preserved
# during mxmake updates.
##############################################################################

##############################################################################
# Coverage targets
##############################################################################

.PHONY: coverage
coverage: $(PACKAGES_TARGET)
	@echo "Run tests with coverage"
	@coverage run -m pytest
	@coverage combine
	@coverage report --show-missing

.PHONY: coverage-html
coverage-html: $(PACKAGES_TARGET)
	@echo "Run tests with coverage and generate HTML report"
	@coverage run -m pytest
	@coverage combine
	@coverage html
	@echo "Opening coverage report..."
	@which xdg-open > /dev/null && xdg-open htmlcov/index.html || \
	 which open > /dev/null && open htmlcov/index.html || \
	 echo "Open htmlcov/index.html in your browser"
